import gradio as gr
from main import generate_project_with_progress

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."

def gradio_all_in_one(task, system_prompt):
    # Combine prompt, code generation, and live logs in one function
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT
    # The backend generator yields all progress (AI, file, folder creation)
    for progress in generate_project_with_progress(task):
        yield progress

with gr.Blocks(theme=gr.themes.Base(), css=".gradio-container {max-width: 900px; margin: auto;}") as demo:
    gr.Markdown("# <span style='color:#4F8EF7'>PySprit Unified AI Project Generator</span>", elem_id="title")
    gr.Markdown("Enter your project prompt below. The AI will generate code, create files and folders, and display all progress live.")
    ai_status = gr.Markdown("*Status:* 🟢 Idle", elem_id="ai_status")
    with gr.Row():
        task = gr.Textbox(label="What do you want to build? (Prompt)", lines=3, interactive=True)
        system_prompt = gr.Textbox(label="System Prompt (optional)", value=DEFAULT_SYSTEM_PROMPT, lines=2)
    generate_btn = gr.Button("Generate Project", variant="primary")
    live_code = gr.Code(label="Live AI Code (Streaming)", language="python", lines=16, interactive=False)
    def run_with_status(task, system_prompt):
        # This function wraps the generator and yields status updates
        yield gr.update(value="*Status:* 🟡 AI is generating code...")
        for progress in generate_project_with_progress(task):
            if progress.startswith("✨ AI finished generating code.") or progress.startswith("\n✨ All done!"):
                yield gr.update(value="*Status:* 🟢 Done")
            elif progress.startswith("❌"):
                yield gr.update(value=f"*Status:* 🔴 Error: {progress}")
            else:
                yield gr.update()
    generate_btn.click(run_with_status, inputs=[task, system_prompt], outputs=ai_status, show_progress=True)
    generate_btn.click(fn=gradio_all_in_one, inputs=[task, system_prompt], outputs=live_code, show_progress=True)

if __name__ == "__main__":
    demo.launch()
