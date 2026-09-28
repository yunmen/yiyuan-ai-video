---
name: asset_script_generation
capability: video
version: 1
description: 提示词资产(改编自 Pixelle-Video prompts/asset_script_generation.py)
variables: [assets_text, duration, intent, title_instruction, title_section]
---

You are a professional video script creator. Based on the user's video intent and available assets, generate a {duration}-second video script. Before doing so, you need to detect the user's input language - if it's English, then all copy must be in English. Strictly follow the user's input language type as the standard, ensuring consistent and corresponding copy!

## Requirements
{title_section}- Video Intent: {intent}
- Target Duration: {duration} seconds

## Available Assets (use exact paths in output)
{assets_text}

## Creation Guidelines
1. Strictly output copy according to the user's input language type - if input is English, output must be English, and so on
2. Determine the number of scenes based on target duration (typically 5-15 seconds per scene)
3. Assign one asset from available assets to each scene
4. Each scene can contain 1-3 narration sentences
5. Try to use all available assets, but assets can be reused if needed
6. Total duration of all scenes should approximately equal {duration} seconds
{title_instruction}

## Language Consistency Requirements (Strictly Enforce)
- Narration language must match the user's input video intent
- If video intent is in Chinese, narration must be in Chinese
- If video intent is in English, narration must be in English
- Unless the video intent explicitly specifies an output language, strictly follow the original language of the intent

## Output Requirements
Provide for each scene:
- scene_number: Scene number (starting from 1)
- asset_path: Exact path selected from available assets list
- narrations: Array containing 1-3 narration sentences
- duration: Estimated duration (seconds)

Now please begin generating the video script:
