import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import asyncio
import json
from duckduckgo_search import DDGS
import newspaper
from newspaper import Article, Config
import ollama
import os

# ENV CONFIG
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
news_config = Config()
news_config.browser_user_agent = USER_AGENT
news_config.request_timeout = 10

def load_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

try:
    config = load_config('deno.json')
    print("Loaded config:", config)
except Exception as e:
    print("No deno.json config or error:", e)
    config = {}

def is_search_command(query: str) -> bool:
    return query.lower().startswith("search ")

# MAIN APP
class CheapGPTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CheapGPT Agent")
        self.geometry("1200x800")
        self.configure(bg="#ffffff")
        try:
            self.iconbitmap("pig.ico")
        except Exception as e:
            print("Warning: pig.ico not set:", e)

        self.models = {
            "huihui_ai/llama3.2-abliterate:latest": {"size": "2.2 GB", "web_search": True},
            "llava-phi3:latest": {"size": "2.9 GB", "web_search": True},
            "mannix/llama3.1-8b-abliterated:latest": {"size": "4.7 GB", "web_search": True},
            "deepseek-r1:7b": {"size": "4.7 GB", "web_search": True},
            "qwen2.5-coder:0.5b": {"size": "531 MB", "web_search": True},
            "llama3.2:latest": {"size": "2.0 GB", "web_search": True},
            "llama3.2:3b": {"size": "2.0 GB", "web_search": True},
            "llama2:latest": {"size": "3.8 GB", "web_search": True},
            "qwen2.5-coder:3b": {"size": "1.9 GB", "web_search": True}
        }

        self.current_model = "huihui_ai/llama3.2-abliterate:latest"
        self.model_var = tk.StringVar(value=self.current_model)
        self.conversation = []
        self.mode = None
        self.current_image = None

        self.colors = {
            "bg": "#1e1e1e",
            "text": "#ffffff",
            "secondary_text": "#808080",
            "tile_bg": "#2d2d2d",
            "tile_hover": "#3d3d3d",
            "button_bg": "#4a4a4a"
        }
        
        self.build_ui()

    def build_ui(self):
        header = tk.Frame(self, bg="#1e1e1e", height=60)
        header.pack(side=tk.TOP, fill=tk.X)

        models_frame = tk.Frame(header, bg="#1e1e1e")
        models_frame.pack(side=tk.LEFT, padx=20)
        
        self.models_btn = ttk.Menubutton(models_frame, text="MODELS ▼", style="Bold.TMenubutton")
        self.models_btn.pack(side=tk.LEFT, pady=15)
        
        self.update_model_menu()

        main_frame = tk.Frame(self, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Ask CheapGPT AI Anything", font=("Helvetica", 32, "bold"), bg="white", fg="black").pack(pady=(50,30))
        tk.Label(main_frame, text="Used by 1 person", fg="gray", bg="white").pack(pady=10)

        tiles_frame = tk.Frame(main_frame, bg="white")
        tiles_frame.pack(pady=20)
        self.create_feature_tile(tiles_frame, "🌐", "Web Search with\nCitations", self.set_mode_web)
        self.create_feature_tile(tiles_frame, "📄", "Image/Docs/Code\nAnalysis", self.set_mode_image)

        self.conversation_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("Helvetica", 11), bg="white", height=15)
        self.conversation_area.pack(pady=10, padx=40, fill=tk.BOTH, expand=True)

        self.image_status = tk.Label(main_frame, text="No image selected", bg="white", fg="gray")
        self.image_status.pack(pady=5)

        input_frame = tk.Frame(self, bg="white", pady=20)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=40)

        self.user_input = ttk.Entry(input_frame, font=("Helvetica", 12))
        self.user_input.pack(fill=tk.X, pady=(0,10))
        self.user_input.insert(0, "Message CheapGPT or @mention agent")
        self.user_input.bind("<FocusIn>", self.clear_placeholder)
        self.user_input.bind("<FocusOut>", self.restore_placeholder)
        self.user_input.bind("<Return>", self.handle_input)

        tools_frame = tk.Frame(input_frame, bg="white")
        tools_frame.pack(fill=tk.X)
        tools = [("🌐 Web Search", None), ("📤 Upload", self.upload_image)]
        for tool, cmd in tools:
            btn = ttk.Button(tools_frame, text=tool, style="TButton", command=cmd)
            btn.pack(side=tk.LEFT, padx=2)

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.handle_input, style="TButton")
        self.send_btn.pack(side=tk.RIGHT, padx=5)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TButton", background="#4a4a4a", foreground="white", font=("Helvetica", 10))
        self.style.configure("Bold.TMenubutton", background="#1e1e1e", foreground="white", font=("Helvetica", 12, "bold"))
        self.style.map("TButton", background=[('active', '#3d3d3d')])
        self.style.map("Bold.TMenubutton", background=[('active', '#3d3d3d')])

    def update_model_menu(self):
        models_menu = tk.Menu(self.models_btn, tearoff=0, font=("Helvetica", 10, "bold"))
        self.models_btn["menu"] = models_menu
        for model in self.models.keys():
            label = f"✓ {model}" if model == self.current_model else f"  {model}"
            models_menu.add_command(label=label, command=lambda m=model: self.select_model(m))

    def create_feature_tile(self, parent, emoji, title, command):
        tile = tk.Frame(parent, bg="white", bd=1, relief=tk.SOLID)
        tile.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=15)
        tk.Label(tile, text=emoji, font=("Segoe UI Emoji", 24), bg="white").pack(pady=5)
        tk.Label(tile, text=title, font=("Helvetica", 12), bg="white").pack(pady=5)
        ttk.Button(tile, text="Open", command=command, style="TButton").pack(pady=5)

    def clear_placeholder(self, event):
        if self.user_input.get() == "Message CheapGPT or @mention agent":
            self.user_input.delete(0, tk.END)

    def restore_placeholder(self, event):
        if not self.user_input.get():
            self.user_input.insert(0, "Message CheapGPT or @mention agent")

    def select_model(self, model_name):
        if self.mode == "image" and model_name != "llava-phi3:latest":
            self.append_system("Image mode only supports llava-phi3:latest.")
            return
        self.current_model = model_name
        self.update_model_menu()
        self.append_system(f"Switched to model: {model_name}")

    def set_mode_web(self):
        self.mode = "web"
        self.image_status.config(text="")
        self.append_system("Mode set to Web Search. Type 'search <query>' to do a web search, or chat normally.")

    def set_mode_image(self):
        self.mode = "image"
        self.current_model = "llava-phi3:latest"
        self.update_model_menu()
        self.current_image = None
        self.image_status.config(text="No image selected")
        self.append_system("Mode set to Image Q&A with 'llava-phi3:latest'. Chat normally or use the Upload button/type 'select image' to add an image.")

    def upload_image(self):
        if self.mode != "image":
            self.append_system("Please switch to Image mode to upload an image.")
            return
        image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if image_path:
            self.current_image = image_path
            self.image_status.config(text=f"Selected image: {os.path.basename(image_path)}")
            self.append_system(f"Image selected: {os.path.basename(image_path)}")
        else:
            self.append_system("No image selected.")

    def handle_input(self, event=None):
        query = self.user_input.get().strip()
        if not query:
            return
        self.user_input.delete(0, tk.END)
        self.user_input.configure(state='disabled')
        self.send_btn.configure(state='disabled')

        if not self.mode:
            self.append_system("No mode selected. Please click one of the tiles above.")
            self.enable_input()
            return

        if self.mode == "web":
            self.append_message({'role': 'user', 'content': query})
            if is_search_command(query):
                actual_query = query[7:].strip()
                threading.Thread(target=self.process_web_search, args=(actual_query,), daemon=True).start()
            else:
                threading.Thread(target=self.process_query, daemon=True).start()
        elif self.mode == "image":
            if query.lower() == "select image":
                image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
                if image_path:
                    self.current_image = image_path
                    self.image_status.config(text=f"Selected image: {os.path.basename(image_path)}")
                    self.append_system(f"Image selected: {os.path.basename(image_path)}")
                else:
                    self.append_system("No image selected.")
                self.enable_input()
            else:
                # Allow normal chat if no image, or include image if selected
                msg = {'role': 'user', 'content': query}
                if self.current_image:
                    msg['images'] = [self.current_image]
                self.append_message(msg)
                threading.Thread(target=self.process_query, daemon=True).start()

    def append_message(self, msg):
        text = f"You: {msg['content']}" if msg['role'] == 'user' else f"AI: {msg['content']}" if msg['role'] == 'assistant' else f"System: {msg['content']}"
        if msg['role'] == 'user' and 'images' in msg:
            text += " [Image attached]"
        self.conversation_area.configure(state='normal')
        self.conversation_area.insert(tk.END, text + "\n\n")
        self.conversation_area.configure(state='disabled')
        self.conversation_area.see(tk.END)
        self.conversation.append(msg)

    def append_system(self, msg):
        self.append_message({'role': 'system', 'content': msg})

    def process_web_search(self, actual_query):
        async def async_process():
            try:
                urls = await self.get_search_results(actual_query)
                if not urls:
                    self.append_system("No search results or error.")
                    self.enable_input()
                    return
                texts = await self.get_cleaned_text(urls)
                if not texts:
                    self.append_system("No relevant info found from the search.")
                    self.enable_input()
                    return
                search_results = ''.join(texts)
                self.append_message({'role': 'system', 'content': f"Search results for '{actual_query}':\n{search_results}"})
                await self.stream_ai_response(self.conversation, self.current_model)
            except Exception as e:
                self.append_system(f"Error: {str(e)}")
            finally:
                self.enable_input()
        asyncio.run(async_process())

    def process_query(self):
        async def async_process():
            try:
                await self.stream_ai_response(self.conversation, self.current_model)
            except Exception as e:
                self.append_system(f"Error: {str(e)}")
            finally:
                self.enable_input()
        asyncio.run(async_process())

    async def stream_ai_response(self, messages, model_name):
        try:
            self.conversation_area.configure(state='normal')
            self.conversation_area.insert(tk.END, "AI: ")
            partial_text = ""
            stream = ollama.chat(model=model_name, messages=messages, stream=True)
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    token = chunk['message']['content']
                    partial_text += token
                    self.conversation_area.insert(tk.END, token)
                    self.conversation_area.see(tk.END)
                    await asyncio.sleep(0.01)
            self.conversation_area.insert(tk.END, "\n\n")
            self.conversation_area.configure(state='disabled')
            self.conversation.append({'role': 'assistant', 'content': partial_text})
        except Exception as e:
            self.append_system(f"Error in response: {str(e)}")
        finally:
            self.enable_input()

    async def get_search_results(self, query):
        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=5)
            return [r['href'] for r in results]
        except Exception as e:
            self.append_system(f"Search error: {str(e)}")
            return []

    async def get_cleaned_text(self, urls):
        texts = []
        for url in urls:
            try:
                article = Article(url, config=news_config)
                await asyncio.to_thread(article.download)
                await asyncio.to_thread(article.parse)
                text = article.text
                texts.append(f"Source: {url}\n{text}\n\n")
                self.append_system(f"Processed: {url}")
            except Exception as e:
                self.append_system(f"Error processing {url}: {str(e)}")
        return texts

    def enable_input(self):
        self.user_input.configure(state='normal')
        self.send_btn.configure(state='normal')
        self.user_input.focus()

if __name__ == "__main__":
    app = CheapGPTApp()
    app.mainloop()
