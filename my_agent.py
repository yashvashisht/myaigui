import pyautogui
import time
import re
import ctypes
import google.generativeai as genai
from PIL import Image

# =========================
# 1. SETUP & ROBUST MODEL CHECK
# =========================
API_KEY = "AIzaSyBfvSsyrKNNTSZHskhTcx11AdDyxHrc-XQ" # Your Key
genai.configure(api_key=API_KEY)

def find_working_model():
    """Fixes the 'generator not subscriptable' and '404' errors."""
    try:
        # Convert generator to a list properly
        available_models = list(genai.list_models())
        
        # Look for the exact string the API currently wants
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                if "gemini-1.5-flash" in m.name:
                    return m.name # Returns 'models/gemini-1.5-flash'
        
        # If flash isn't found, get the first compatible model
        for m in available_models:
            if 'generateContent' in m.supported_generation_methods:
                return m.name
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
    return "models/gemini-1.5-flash" # Absolute fallback string

MODEL_ID = find_working_model()
print(f"✅ System Ready. Using Model: {MODEL_ID}")

# Standard UI Safety
pyautogui.FAILSAFE = True
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# =========================
# 2. VISION & EXECUTION LOGIC
# =========================

def call_gemini(prompt, image=None):
    """Handles API calls with automatic retry for rate limits."""
    model = genai.GenerativeModel(MODEL_ID)
    while True:
        try:
            if image:
                # Use standard generation (latest SDK format)
                response = model.generate_content([prompt, image])
            else:
                response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                print("⏳ Quota full. Waiting 20s...")
                time.sleep(20)
            else:
                print(f"⚠️ API Error: {e}")
                return None

def execute_action(instruction):
    print(f"\n🚀 Attempting: {instruction}")
    
    # 1. Capture screen
    screenshot = pyautogui.screenshot()
    w, h = screenshot.size

    # 2. AI Coordinate Prompt
    prompt = f"""
    Find the center of: {instruction}
    Return 0-1000 normalized coordinates.
    Format:
    REASONING: [brief description]
    COORD: [x, y]
    """

    res = call_gemini(prompt, screenshot)
    if not res: return False

    # 3. Parse and Click
    match = re.search(r"COORD:\s*\[(\d+),\s*(\d+)\]", res)
    if match:
        nx, ny = int(match.group(1).strip()), int(match.group(2).strip())
        tx = int((nx / 1000) * w)
        ty = int((ny / 1000) * h)

        print(f"🎯 Moving to {tx}, {ty}")
        pyautogui.moveTo(tx, ty, duration=1.0)
        time.sleep(0.2)
        
        # Smart click logic
        if "open" in instruction.lower() or "double" in instruction.lower():
            pyautogui.doubleClick()
        else:
            pyautogui.click()
        return True
    
    print("❌ AI could not pinpoint coordinates.")
    return False

# =========================
# 3. SMART TASK HANDLER
# =========================

def run_agent(goal):
    # Special shortcut for "Open [App]" tasks
    # It's much faster to use the Windows Key than searching for icons
    if "open" in goal.lower() and len(goal.split()) < 5:
        app_name = goal.lower().replace("open", "").strip()
        print(f"⌨️ Using keyboard shortcut to open {app_name}...")
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(app_name, interval=0.1)
        time.sleep(0.5)
        pyautogui.press('enter')
        print("✅ Command sent.")
        return

    # For everything else, use Vision
    print(f"🧠 Thinking: {goal}")
    plan_prompt = f"Break the task '{goal}' into 1-2 UI action lines. Be very brief."
    plan_raw = call_gemini(plan_prompt)
    if not plan_raw: return

    steps = [s.strip("0123456789. ") for s in plan_raw.strip().splitlines() if s.strip()]
    for step in steps:
        if not execute_action(step): break
        time.sleep(2)

if __name__ == "__main__":
    task = input("What should I do? ")
    run_agent(task)