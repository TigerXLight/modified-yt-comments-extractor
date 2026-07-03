from pathlib import Path
import re

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# 1. Add ASR metadata state in __init__
if "self.last_asr_metadata" not in s:
    s = s.replace(
        "        self.last_youtube_video_info: Optional[Dict[str, Any]] = None\n"
        "        self.last_package_dir: Optional[str] = None\n",
        "        self.last_youtube_video_info: Optional[Dict[str, Any]] = None\n"
        "        self.last_asr_metadata: Optional[Dict[str, Any]] = None\n"
        "        self.last_package_dir: Optional[str] = None\n",
    )

# 2. Store ASR metadata after successful local ASR
if "self.last_asr_metadata = metadata" not in s:
    s = s.replace(
        "                    self.transcript_segments = segments\n"
        "                    self.last_youtube_video_info = None\n",
        "                    self.transcript_segments = segments\n"
        "                    self.last_youtube_video_info = None\n"
        "                    self.last_asr_metadata = metadata\n",
        1,
    )

# 3. Clear ASR metadata when YouTube transcript metadata is set
if "self.last_asr_metadata = None\n                    self.last_youtube_video_info = video_info or None" not in s:
    s = s.replace(
        "                    self.last_youtube_video_info = video_info or None\n",
        "                    self.last_asr_metadata = None\n"
        "                    self.last_youtube_video_info = video_info or None\n",
    )

# 4. Clear ASR metadata when a transcript is manually imported
if "self.last_asr_metadata = None\n            self.last_youtube_video_info = None\n            self.last_transcript_source = f\"Imported transcript" not in s:
    s = s.replace(
        "            self.transcript_segments = segments\n"
        "            self._refresh_transcript_display()\n",
        "            self.transcript_segments = segments\n"
        "            self.last_asr_metadata = None\n"
        "            self.last_youtube_video_info = None\n"
        "            self.last_transcript_source = f\"Imported transcript from {os.path.basename(filename)}\"\n"
        "            self._refresh_transcript_display()\n",
        1,
    )

# 5. Clear ASR metadata when transcript is cleared
if "self.last_asr_metadata = None" in s and "def clear_transcript" in s:
    s = re.sub(
        r"(    def clear_transcript\(self\) -> None:\n(?:        .*\n){0,20}?        self\.last_transcript_source = None\n)",
        r"\1        self.last_asr_metadata = None\n",
        s,
        count=1,
    )

# 6. Add method that appends ASR metadata to source_info.txt
if "def _append_asr_metadata_to_source_info" not in s:
    method = '''
    def _append_asr_metadata_to_source_info(self, package_dir: str) -> None:
        """Append Local ASR metadata to source_info.txt when available."""
        if not self.last_asr_metadata:
            return

        info = self.last_asr_metadata
        source_info_path = os.path.join(package_dir, "source_info.txt")

        probability = info.get("language_probability")

        if probability is not None:
            try:
                probability_text = f"{float(probability):.2%}"
            except Exception:
                probability_text = str(probability)
        else:
            probability_text = "unknown"

        fields = [
            ("Source File", "source_file"),
            ("Model", "model_name"),
            ("Device", "device"),
            ("Compute Type", "compute_type"),
            ("Speaker Label", "speaker_name"),
            ("Language Setting", "requested_language"),
            ("Detected Language", "language"),
            ("Language Confidence", None),
            ("Known Words / Context Prompt", "initial_prompt"),
            ("VAD Filter", "vad_filter"),
            ("Beam Size", "beam_size"),
            ("Segment Count", "segment_count"),
            ("Duration", "duration"),
            ("Duration After VAD", "duration_after_vad"),
        ]

        lines = []
        lines.append("")
        lines.append("")
        lines.append("Local ASR Metadata")
        lines.append("=" * 80)

        for label, key in fields:
            if key is None:
                value = probability_text
            else:
                value = info.get(key)

            if value not in (None, ""):
                lines.append(f"{label}: {value}")

        lines.append("")
        lines.append("Note")
        lines.append("-" * 80)
        lines.append(
            "Local ASR transcripts are machine-generated drafts. "
            "They may contain transcription errors and do not include speaker diarization."
        )
        lines.append("")

        with open(source_info_path, "a", encoding="utf-8", newline="\\n") as f:
            f.write("\\n".join(lines))
'''

    s = s.replace(
        "    def export_evidence_folder(self) -> None:\n",
        method + "\n    def export_evidence_folder(self) -> None:\n",
        1,
    )

# 7. Call the ASR metadata append method after package creation
if "self._append_asr_metadata_to_source_info(package_dir)" not in s:
    if "self._append_youtube_metadata_to_source_info(package_dir)" in s:
        s = s.replace(
            "            self._append_youtube_metadata_to_source_info(package_dir)\n",
            "            self._append_youtube_metadata_to_source_info(package_dir)\n"
            "            self._append_asr_metadata_to_source_info(package_dir)\n",
            1,
        )
    else:
        s = s.replace(
            "            self.log_message(f\"Export package created: {package_dir}\", \"success\")\n",
            "            self._append_asr_metadata_to_source_info(package_dir)\n\n"
            "            self.log_message(f\"Export package created: {package_dir}\", \"success\")\n",
            1,
        )

p.write_text(s, encoding="utf-8")
print("ASR metadata patch applied.")