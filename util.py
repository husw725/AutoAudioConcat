import os
import tempfile
import numpy as np
import torch
import soundfile as sf
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook


class PyannoteSpeakerDiarizationUtil:
    """
    使用 pyannote/speaker-diarization-community-1 实现说话人分离的工具类。
    支持传入音频文件路径或 waveform + sample_rate。
    """

    def __init__(self, hf_token: str, cache_dir: str = "./models/pyannote", use_gpu: bool = True):
        """
        初始化说话人分离工具。

        :param hf_token: HuggingFace 访问令牌
        :param cache_dir: 模型缓存目录
        :param use_gpu: 是否使用 GPU（若可用）
        """
        self.hf_token = hf_token
        self.cache_dir = cache_dir
        self.use_gpu = use_gpu
        self.pipeline = None

    def _load_pipeline(self):
        """延迟加载 pyannote pipeline"""
        if self.pipeline is None:
            print("[Pyannote 4.1] Loading speaker diarization pipeline...")
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1",
                token=self.hf_token,
                cache_dir=self.cache_dir,
            )
            if self.use_gpu and torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
                print("[Pyannote 4.1] Using GPU")
            else:
                print("[Pyannote 4.1] Using CPU")

    def _prepare_audio_file(self, audio=None, audio_path: str = "") -> str:
        """根据输入类型准备音频文件路径"""
        if audio is not None:
            if isinstance(audio, dict) and "waveform" in audio and "sample_rate" in audio:
                waveform = audio["waveform"]
                sample_rate = audio["sample_rate"]
            elif isinstance(audio, (tuple, list)) and len(audio) == 2:
                waveform, sample_rate = audio
            else:
                raise ValueError(f"Invalid audio input type: {type(audio)}")

            if hasattr(waveform, "cpu"):
                waveform = waveform.cpu().numpy()
            waveform = np.squeeze(waveform)
            if waveform.ndim == 2 and waveform.shape[0] < waveform.shape[1]:
                waveform = waveform.T

            tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sf.write(tmp_file.name, waveform, sample_rate)
            print(f"[Pyannote 4.1] Using waveform input -> temp file: {tmp_file.name}")
            return tmp_file.name

        elif audio_path and os.path.exists(audio_path):
            print(f"[Pyannote 4.1] Using audio_path: {audio_path}")
            return audio_path
        else:
            raise ValueError("Please provide either 'audio' or a valid 'audio_path'")

    def diarize(self, audio=None, audio_path: str = "") -> list:
        """
        运行说话人分离。

        :param audio: 可选，包含 waveform 和 sample_rate 的 dict 或 tuple
        :param audio_path: 可选，音频文件路径
        :return: 说话人分段结果列表，例如：
            [
                {"start": 0.12, "end": 2.45, "speaker": "speaker_0"},
                {"start": 2.46, "end": 4.98, "speaker": "speaker_1"},
                ...
            ]
        """
        self._load_pipeline()
        audio_file = self._prepare_audio_file(audio, audio_path)

        print(f"[Pyannote 4.1] Running diarization on {audio_file}...")
        with ProgressHook() as hook:
            output = self.pipeline(audio_file, hook=hook)

        result = [
            {"start": round(turn.start, 2), "end": round(turn.end, 2), "speaker": f"speaker_{speaker}"}
            for turn, speaker in output.itertracks(yield_label=True)
        ]

        print(f"[Pyannote 4.1] Found {len(result)} segments")

        # 清理临时文件（如果有）
        if audio is not None and not isinstance(audio, str) and os.path.exists(audio_file):
            os.remove(audio_file)

        return result