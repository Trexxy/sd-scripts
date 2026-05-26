import json
import os
import random
from pathlib import Path

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


def _find_adetailer_script(p):
    for script in getattr(p.scripts, "alwayson_scripts", []):
        if Path(script.filename).stem == "!adetailer":
            return script
    return None


class HiresCheckpointRandomizer(scripts.Script):
    def title(self):
        return "Hires Checkpoint Randomizer"

    def show(self, is_img2img):
        return False if is_img2img else scripts.AlwaysVisible

    def ui(self, is_img2img):
        choices = sorted(sd_models.checkpoint_tiles(use_short=True), key=str.casefold)

        with gr.Accordion("Hires Checkpoint Randomizer", open=False):
            enabled = gr.Checkbox(label="Enable", value=False)
            with gr.Row():
                checkpoints = gr.Dropdown(
                    label="Checkpoints to randomize",
                    choices=choices,
                    value=[],
                    multiselect=True,
                )
                refresh_btn = ToolButton(value=_REFRESH_SYMBOL, tooltip="Refresh checkpoint list")

        def on_enable(enabled_val):
            if not enabled_val:
                return gr.update()
            saved = _load_config()
            new_choices = sorted(sd_models.checkpoint_tiles(use_short=True), key=str.casefold)
            choices_set = set(new_choices)
            value = []
            for name in saved:
                info = sd_models.get_closet_checkpoint_match(name)
                if info is not None and info.short_title in choices_set:
                    value.append(info.short_title)
            return gr.update(choices=new_choices, value=value)

        def on_refresh():
            return gr.update(choices=sorted(sd_models.checkpoint_tiles(use_short=True), key=str.casefold))

        enabled.change(fn=on_enable, inputs=[enabled], outputs=[checkpoints])
        refresh_btn.click(fn=on_refresh, outputs=[checkpoints])
        checkpoints.change(fn=_save_config, inputs=[checkpoints])

        return [enabled, checkpoints]

    def before_process(self, p, enabled, selected_checkpoints):
        if not enabled or not selected_checkpoints:
            return

        # ADetailer calls p.scripts.before_process(copy(p)) after each image via
        # need_call_process. copy(p) is shallow, so script_args is shared — a fresh
        # random.choice here would overwrite the AD checkpoint while p.hr_checkpoint_name
        # stays unchanged, causing divergence. Store on p so re-invocations reuse it.
        if not hasattr(p, "_hcr_chosen"):
            p._hcr_chosen = random.choice(selected_checkpoints)
        chosen = p._hcr_chosen

        if getattr(p, "enable_hr", False):
            p.hr_checkpoint_name = chosen

        if p.scripts is not None:
            ad_script = _find_adetailer_script(p)
            if ad_script is not None:
                if isinstance(p.script_args, tuple):
                    p.script_args = list(p.script_args)
                for i in range(ad_script.args_from, ad_script.args_to):
                    if i < len(p.script_args) and isinstance(p.script_args[i], dict):
                        p.script_args[i] = {**p.script_args[i], "ad_checkpoint": chosen, "ad_use_checkpoint": True}
