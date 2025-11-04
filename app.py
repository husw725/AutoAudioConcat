import os
import json
from pydub import AudioSegment
import streamlit as st

def load_segments_from_folder(folder_path):
    """
    从指定目录加载所有音频片段信息
    假设每个片段有相同名字的 .wav 和 .txt
    .txt 内容为 JSON 格式: {"start": float, "end": float, "speaker": str}
    """
    segments = []
    for fname in os.listdir(folder_path):
        if fname.endswith(".wav"):
            base = os.path.splitext(fname)[0]
            wav_path = os.path.join(folder_path, fname)
            txt_path = os.path.join(folder_path, base + ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                segments.append({
                    "id": base,
                    "wav": wav_path,
                    "start": info.get("start", 0),
                    "end": info.get("end", 0),
                    "speaker": info.get("speaker", "")
                })
    # 按文件名（数字）排序
    segments.sort(key=lambda x: int(x["id"]))
    return segments


def merge_continuous_segments(segments, gap_threshold):
    """
    如果相邻片段的 (next.start - prev.end) < gap_threshold
    则拼接音频。
    """
    merged = []
    if not segments:
        return merged

    current_group = [segments[0]]

    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]
        # 判断是否连续
        if curr["start"] - prev["end"] <= gap_threshold:
            current_group.append(curr)
        else:
            merged.append(current_group)
            current_group = [curr]
    merged.append(current_group)
    return merged


def combine_audio_segments(segment_group):
    """将一个 segment_group 拼接为一条音频"""
    combined = AudioSegment.empty()
    for seg in segment_group:
        combined += AudioSegment.from_wav(seg["wav"])
    return combined


# ---------------- Streamlit UI ----------------
st.title("🎧 连续语音拼接工具")

path = st.text_input("请输入文件夹路径：", value="")
gap_sec = st.number_input("最大允许间隔（秒）", value=2.0, min_value=0.0, step=0.5)

if st.button("开始处理") and path:
    all_results = []

    folders = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    if not folders:
        st.warning("未检测到子文件夹，请确认路径正确。")
    else:
        st.write(f"找到 {len(folders)} 个子文件夹")
        output_dir = os.path.join(path, "merged_results")
        os.makedirs(output_dir, exist_ok=True)

        for folder in folders:
            st.subheader(f"📁 处理子目录：{os.path.basename(folder)}")
            segments = load_segments_from_folder(folder)
            merged_groups = merge_continuous_segments(segments, gap_sec)
            st.write(f"共 {len(merged_groups)} 组连续片段")

            for i, group in enumerate(merged_groups, start=1):
                combined_audio = combine_audio_segments(group)
                output_file = os.path.join(output_dir, f"{os.path.basename(folder)}_group{i}.wav")
                combined_audio.export(output_file, format="wav")
                st.audio(output_file)
                st.write(f"✅ 导出: {output_file}")

        st.success("所有文件夹处理完成 ✅")