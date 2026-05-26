import json
import os
import random

import gradio as gr

import modules.scripts as scripts
from modules import sd_models
from modules.ui_components import ToolButton

_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hires_checkpoint_randomizer_config.json")
_REFRESH_SYMBOL = "\U0001f504"  # 🔄


def _load_config():
    if not os.path.exists(_CONFIG_FILE):
        return []
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("selected_checkpoints", [])
    except Exception:
        return []


def _save_config(selected):
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"selected_checkpoints": selected or []}, f, indent=2)
    except Exception:
        pass


class HiresCheckpointRandomizer(scripts.Script):
    def title(self):
        return "Hires Checkpoint Randomizer"

    def show(self, is_img2img):
        return False if is_img2img else scripts.AlwaysVisible

    def ui(self, is_img2img):
        saved = _load_config()
        choices = sorted(sd_models.checkpoint_tiles(use_short=True), key=str.casefold)
        value = [c for c in saved if c in choices]

        with gr.Accordion("Hires Checkpoint Randomizer", open=False):
            enabled = gr.Checkbox(label="Enable", value=False)
            with gr.Row():
                checkpoints = gr.Dropdown(
                    label="Checkpoints to randomize",
                    choices=choices,
                    value=value,
                    multiselect=True,
                )
                refresh_btn = ToolButton(value=_REFRESH_SYMBOL, tooltip="Refresh checkpoint list")

        def on_refresh():
            new_choices = sorted(sd_models.checkpoint_tiles(use_short=True), key=str.casefold)
            return gr.update(choices=new_choices)

        refresh_btn.click(fn=on_refresh, outputs=[checkpoints])
        checkpoints.change(fn=_save_config, inputs=[checkpoints])

        return [enabled, checkpoints]

    def before_process(self, p, enabled, selected_checkpoints):
        if not enabled or not selected_checkpoints or not getattr(p, "enable_hr", False):
            return

        p.hr_checkpoint_name = random.choice(selected_checkpoints)
