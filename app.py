import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ui.streamlit.app import StreamlitChatApp

if __name__ == "__main__":
    app = StreamlitChatApp()
    app.run()
