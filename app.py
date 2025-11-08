import os
import json
import subprocess
from pydub import AudioSegment
import streamlit as st

# ---------------- ffmpeg 检查 ----------------
def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

# ---------------- 音频处理函数 ----------------
def load_segments_from_folder(folder_path, min_duration_sec=0.0):
    """
    从指定目录加载所有音频片段信息
    支持 .wav、.flac、.mp3
    .txt 内容为 JSON 格式: {"start": float, "end": float, "speaker": str}
    可通过 min_duration_sec 忽略过短片段
    """
    segments = []
    for fname in os.listdir(folder_path):
        if fname.endswith((".wav", ".flac", ".mp3")):
            base = os.path.splitext(fname)[0]
            audio_path = os.path.join(folder_path, fname)
            txt_path = os.path.join(folder_path, base + ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                start = info.get("start", 0)
                end = info.get("end", 0)
                if end - start >= min_duration_sec:  # 忽略过短片段
                    segments.append({
                        "id": base,
                        "audio": audio_path,
                        "start": start,
                        "end": end,
                        "speaker": info.get("speaker", "")
                    })
    segments.sort(key=lambda x: int(x["id"]))  # 按数字文件名排序
    return segments

def merge_continuous_segments(segments, gap_threshold):
    """
    合并连续片段：
    - 相邻文件名必须连续数字
    - start - prev.end <= gap_threshold
    """
    merged = []
    if not segments:
        return merged

    current_group = [segments[0]]
    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]
        prev_id = int(prev["id"])
        curr_id = int(curr["id"])
        if curr_id == prev_id + 1 and (curr["start"] - prev["end"] <= gap_threshold):
            current_group.append(curr)
        else:
            merged.append(current_group)
            current_group = [curr]
    merged.append(current_group)
    return merged

def combine_audio_segments(segment_group):
    """将一个 segment_group 拼接为一条音频（自动识别格式）"""
    combined = AudioSegment.empty()
    for seg in segment_group:
        path = seg["audio"]
        try:
            combined += AudioSegment.from_file(path)
        except Exception as e:
            st.error(f"❌ 无法解码文件 {path} ：{e}")
    return combined

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="连续语音拼接工具", layout="wide")
st.title("🎧 连续语音拼接工具")

if not check_ffmpeg():
    st.error("❌ 未检测到 ffmpeg，请先安装 ffmpeg 并确保可执行文件在 PATH 中")
    st.stop()

# 输入参数
path = st.text_input("请输入输入文件夹路径：", value="")
output_dir = st.text_input("请输入输出目录路径：", value=os.path.join(path, "merged_results"))
gap_sec = st.number_input("最大允许间隔（秒）", value=2.0, min_value=0.0, step=0.5)
min_duration_sec = st.number_input("忽略过短片段（秒，小于此值将跳过）", value=0.5, min_value=0.0, step=0.1)

if st.button("开始处理") and path:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 获取子文件夹
    folders = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    if not folders:
        st.warning("未检测到子文件夹，请确认路径正确。")
    else:
        st.write(f"找到 {len(folders)} 个子文件夹")
        st.write(f"输出目录：{output_dir}")

        # 处理每个子文件夹
        for folder in folders:
            st.subheader(f"📁 处理子目录：{os.path.basename(folder)}")
            segments = load_segments_from_folder(folder, min_duration_sec=min_duration_sec)
            merged_groups = merge_continuous_segments(segments, gap_sec)
            st.write(f"共 {len(merged_groups)} 组连续片段")

            for i, group in enumerate(merged_groups, start=1):
                combined_audio = combine_audio_segments(group)
                output_file = os.path.join(output_dir, f"{os.path.basename(folder)}_group{i}.wav")
                combined_audio.export(output_file, format="wav")
                st.audio(output_file)
                st.write(f"✅ 导出: {output_file}")

        st.success("所有文件夹处理完成 ✅")