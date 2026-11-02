"""Worker + endpoint WebSocket para análisis de comentarios de TikTok Live en tiempo real.

Flujo:
    1. El frontend abre un WS a /api/live/{usuario}.
    2. El servidor levanta un LiveWorker que se conecta al chat de TikTok.
    3. Por cada comentario que llega, lo clasifica y empuja un JSON al WS.
    4. Al cerrar el WS (o cuando el live termina), el worker se detiene.

Mensajes que emite por el WebSocket:
    {"tipo": "conectado",     "usuario": "@xxx"}
    {"tipo": "comentario",    "texto": "...", "autor": "nick", "clase": "Pedido",
                              "probabilidad": 0.92, "probabilidades": {...},
                              "recibido_en": "2026-11-02T14:00:00Z"}
    {"tipo": "estado",        "comentarios_capturados": 42}
    {"tipo": "desconectado",  "razon": "fin del live"}
    {"tipo": "error",         "mensaje": "..."}

El frontend puede enviar:
    {"accion": "detener"}
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import text

from api.service import ModelService
from src import db

log = logging.getLogger("comentaventa.live")


class LiveWorker:
    """Un worker por conexión WebSocket. Se conecta a TikTok, clasifica y
    empuja los eventos al WS."""

    def __init__(self, usuario: str, websocket: WebSocket, service: ModelService):
        self.usuario = usuario.lstrip("@")
        self.websocket = websocket
        self.service = service
        self.client = None
        self.sesion_id: int | None = None
        self.conteo = 0

    async def _send(self, payload: dict) -> None:
        try:
            await self.websocket.send_json(payload)
        except Exception:
            # El WS puede estar cerrado; es responsabilidad del caller detenerse.
            pass

    def _registrar_sesion(self) -> None:
        engine = db.get_engine()
        if engine is None:
            return
        try:
            with engine.begin() as conn:
                row = conn.execute(text(
                    "INSERT INTO live_sesiones (usuario_tiktok, modo) "
                    "VALUES (:u, 'real') RETURNING id"
                ), {"u": self.usuario}).scalar_one()
                self.sesion_id = int(row)
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo registrar la sesión de live: %s", exc)

    def _guardar_comentario(self, texto: str, clase: str, probabilidad: float) -> None:
        engine = db.get_engine()
        if engine is None or self.sesion_id is None:
            return
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO live_comentarios (sesion_id, texto, clase, probabilidad) "
                    "VALUES (:s, :t, :c, :p)"
                ), {"s": self.sesion_id, "t": texto, "c": clase, "p": probabilidad})
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo guardar el comentario del live: %s", exc)

    def _cerrar_sesion(self) -> None:
        engine = db.get_engine()
        if engine is None or self.sesion_id is None:
            return
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    "UPDATE live_sesiones SET terminada = now(), total_comentarios = :c "
                    "WHERE id = :s"
                ), {"c": self.conteo, "s": self.sesion_id})
        except Exception:  # noqa: BLE001
            pass

    async def start(self) -> None:
        """Conecta a TikTok y empieza a escuchar eventos. Devuelve cuando el live
        termina o la conexión se corta."""
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
        except ImportError:
            await self._send({"tipo": "error",
                              "mensaje": "La librería TikTokLive no está instalada."})
            return

        self._registrar_sesion()
        self.client = TikTokLiveClient(unique_id=self.usuario)

        @self.client.on(ConnectEvent)
        async def _on_connect(event):  # noqa: ARG001
            await self._send({"tipo": "conectado", "usuario": self.usuario})

        @self.client.on(CommentEvent)
        async def _on_comment(event):
            texto = (getattr(event, "comment", "") or "").strip()
            if not texto:
                return
            try:
                resultado = self.service.predict([texto])[0]
            except Exception as exc:  # noqa: BLE001
                log.warning("Error al clasificar comentario: %s", exc)
                return
            autor = ""
            try:
                autor = event.user.nickname if event.user else ""
            except Exception:
                pass
            self.conteo += 1
            await self._send({
                "tipo": "comentario",
                "texto": texto,
                "autor": autor,
                "clase": resultado["clase"],
                "probabilidad": resultado["probabilidad"],
                "probabilidades": resultado["probabilidades"],
                "recibido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            self._guardar_comentario(texto, resultado["clase"], resultado["probabilidad"])
            # Guardar también en la tabla general de predicciones.
            self.service.save([texto], [resultado], origin="live")

        @self.client.on(DisconnectEvent)
        async def _on_disconnect(event):  # noqa: ARG001
            await self._send({"tipo": "desconectado", "razon": "fin del live"})

        try:
            await self.client.connect()
        except Exception as exc:  # noqa: BLE001
            await self._send({"tipo": "error", "mensaje": f"No se pudo conectar: {exc}"})

    async def stop(self) -> None:
        try:
            if self.client is not None:
                await self.client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        self._cerrar_sesion()


async def manejar_live(websocket: WebSocket, usuario: str, service: ModelService) -> None:
    """Función que se llama desde el endpoint WebSocket en api/main.py."""
    await websocket.accept()
    if not service.loaded:
        await websocket.send_json({"tipo": "error",
                                   "mensaje": "El modelo no está cargado."})
        await websocket.close()
        return

    worker = LiveWorker(usuario, websocket, service)
    tarea = asyncio.create_task(worker.start())

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue
            if data.get("accion") == "detener":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await worker.stop()
        tarea.cancel()
        try:
            await websocket.close()
        except Exception:
            pass
