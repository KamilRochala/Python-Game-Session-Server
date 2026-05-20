# Python-Game-Session-Server
A Python FastAPI program to control a game session asynchronously, it now works on LAN!

## Server Setup (Hosting the game)

To host the game server on your machine, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KamilRochala/Python-Game-Session-Server.git
   cd Python-Game-Session-Server
   ```

2. **Set up a Virtual Environment:**
   Create a virtual environment to manage dependencies:
   ```bash
   python -m venv .venv
   ```

   **Activate the virtual environment:**
   * **Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell):**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   * **Linux/macOS:**
     ```bash
     source .venv/bin/activate
     ```

3. **Install Dependencies:**
   Install the required Python packages for the server:
   ```bash
   pip install -r server/requirements.txt
   ```

4. **Setup Database:**
   You need to import the database structure/data for the server to function correctly.
   * Open **pgAdmin** (or your preferred PostgreSQL client).
   * Create a new database for the project (if you haven't already).
   * Right-click the database and select **Restore...**
   * Select the `server/TowerClimbBaza` file provided in the repository to import the database schema and data, use plain option of import.

5. **Run the Server:**
   Start the FastAPI server. By setting the host to `0.0.0.0`, everyone on your local network (LAN) will be able to see and connect to your server.
   ```bash
   fastapi dev server/main.py --host 0.0.0.0 --port 8080
   ```
   *Note: You will need to know your machine's local IP address (e.g., `192.168.x.x`) to give to players so they can connect.*

## Client Setup (Playing the game)

Choose one of the methods below to play the game:

### Option A: Play using the Pre-built Release
This is the easiest method if you just want to play.
1. Go to the **Releases** section on the GitHub repository page.
2. Download the latest release `.zip` archive for your operating system.
3. Extract the contents of the zip file.
4. Launch the game executable found inside the extracted folder.

### Option B: Play using Godot Engine (Source Code)
Use this method if you want to modify the game or run it from the source code.
1. Clone this repository if you haven't already.
2. Download and open the **Godot Engine** (version compatible with this project).
3. In the Godot Project Manager, click **Import**.
4. Navigate to the cloned repository and select the `project.godot` file located inside the `client/` folder.
5. Once imported, click **Edit** to open the project, and press **Play** (F5) to run the game.

## How to Connect

1. Once the game is running (either via the release or Godot), look for the text input label in the **bottom right corner** of the screen.
2. Input the Server Host's local IP address (e.g., `192.168.1.100`) into that label.
3. You are good to go!