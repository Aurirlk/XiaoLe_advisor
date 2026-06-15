"""
Silero VAD 语音活动检测器（后端）
用于 WebSocket 流式音频场景的端点检测
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SileroVADDetector:
    """Silero VAD 语音活动检测

    使用 Silero VAD ONNX 模型进行实时语音端点检测。
    支持流式输入：每次传入一个音频 chunk，返回是否检测到语音/端点。
    """

    def __init__(
        self,
        model_dir: str | Path = "models/snakers4_silero-vad",
        threshold: float = 0.5,
        threshold_low: float = 0.3,
        min_silence_ms: int = 200,
        min_speech_ms: int = 250,
        sample_rate: int = 16000,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.threshold = threshold
        self.threshold_low = threshold_low
        self.min_silence_ms = min_silence_ms
        self.min_speech_ms = min_speech_ms
        self.sample_rate = sample_rate
        self._model = None
        self._is_speech = False
        self._silence_frames = 0
        self._speech_frames = 0
        self._frame_ms = 512000 / sample_rate  # 每帧毫秒数

    def _load_model(self):
        if self._model is not None:
            return
        try:
            import torch
            model_path = self.model_dir / "silero_vad.onnx"
            if not model_path.exists():
                logger.warning("Silero VAD 模型不存在: %s，使用能量检测降级", model_path)
                self._model = "energy_fallback"
                return
            self._model = torch.jit.load(str(model_path))
            self._model.eval()
            logger.info("Silero VAD 模型加载成功: %s", model_path)
        except Exception as e:
            logger.warning("Silero VAD 模型加载失败: %s，使用能量检测降级", e)
            self._model = "energy_fallback"

    def process_chunk(self, audio_chunk: bytes) -> tuple[bool, bool]:
        """处理一个音频 chunk

        Args:
            audio_chunk: PCM 16-bit 16kHz 单声道音频数据

        Returns:
            (is_speech, is_endpoint)
            - is_speech: 当前 chunk 是否包含语音
            - is_endpoint: 是否检测到语音端点（说完了一句话）
        """
        self._load_model()

        if self._model == "energy_fallback":
            return self._energy_detect(audio_chunk)

        try:
            import torch
            import numpy as np
            audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            tensor = torch.from_numpy(audio).unsqueeze(0)
            with torch.no_grad():
                prob = self._model(tensor, self.sample_rate).item()
            return self._update_state(prob)
        except Exception as e:
            logger.warning("VAD 推理失败: %s，回退到能量检测", e)
            return self._energy_detect(audio_chunk)

    def _energy_detect(self, audio_chunk: bytes) -> tuple[bool, bool]:
        """基于能量的简单 VAD 降级方案"""
        import struct
        if len(audio_chunk) < 2:
            return False, False
        samples = struct.unpack(f"<{len(audio_chunk)//2}h", audio_chunk)
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        prob = min(rms / 5000.0, 1.0)
        return self._update_state(prob)

    def _update_state(self, prob: float) -> tuple[bool, bool]:
        is_speech_now = prob >= self.threshold
        is_endpoint = False

        if is_speech_now:
            self._speech_frames += 1
            self._silence_frames = 0
            self._is_speech = True
        else:
            self._silence_frames += 1
            if self._is_speech and self._silence_ms() >= self.min_silence_ms:
                if self._speech_ms() >= self.min_speech_ms:
                    is_endpoint = True
                self._is_speech = False
                self._speech_frames = 0

        return self._is_speech, is_endpoint

    def _silence_ms(self) -> float:
        return self._silence_frames * self._frame_ms

    def _speech_ms(self) -> float:
        return self._speech_frames * self._frame_ms

    def reset(self) -> None:
        self._is_speech = False
        self._silence_frames = 0
        self._speech_frames = 0
