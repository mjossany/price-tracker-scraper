# Lambda SAM Debugging Guide

This comprehensive guide explains how to debug your Lambda function locally using SAM with full debugger support, including detailed explanations of what happens at each step.

## 🚀 Quick Start

### Method 1: Automatic Debug (Recommended) ⚡

**One-button debugging** - Everything happens automatically!

```bash
# 1. Set breakpoints in your code (click in the gutter)
# 2. Press F5
# 3. Wait ~20 seconds for build & startup
# 4. Debugger attaches automatically!
```

**What happens automatically:**
- ✅ Kills any existing process on port 5678
- ✅ Activates your Python virtual environment
- ✅ Builds Lambda with SAM (installs Linux-compatible dependencies)
- ✅ Starts Docker container with Lambda runtime
- ✅ Waits for debugpy to be ready
- ✅ Attaches debugger automatically
- ✅ Pauses at your breakpoints

### Method 2: Manual Debug (Two-Step)

If you prefer manual control:

```bash
# 1. In terminal, run the debug script
./debug_sam.sh

# 2. Wait for: "⏳ Waiting for debugger to attach on port 5678..."

# 3. In Cursor/VS Code:
#    - Set breakpoints in your code
#    - Press F5 (or Cmd+Shift+D, then click green arrow)
#    - Select "Attach to SAM Local (Debug)"

# 4. Debug! Code will pause at breakpoints
```

**Why Use SAM Local Debug:**
- ✅ Uses actual AWS Lambda runtime (Python 3.12 on Amazon Linux)
- ✅ Realistic environment matches production
- ✅ Tests packaging/dependencies work correctly
- ✅ Catches platform-specific issues (Mac vs Linux)
- 🐛 Full debugger support with breakpoints
- 🔍 Inspect variables, step through code in real-time

**Trade-offs:**
- 🐢 Initial startup ~20-30 seconds (Docker container)
- 🔨 Requires rebuild after dependency changes
- 🐳 Requires Docker Desktop running

---

## 📁 File Structure

```
project/
├── lambda_function.py              # ✅ Clean production code
├── lambda_function_debug.py        # 🐛 Debug wrapper (DO NOT DEPLOY)
├── debug_sam.sh                    # 🔧 SAM debug helper script
├── infrastructure/
│   ├── template.yaml               # Production SAM template
│   └── template-debug.yaml         # Debug SAM template
└── .vscode/
    └── launch.json                 # Debugger configuration
```

## 🎯 Debug Configuration

### Attach to SAM Local (Debug)
- Attaches to SAM running with `--debug-port 5678`
- Uses real Lambda runtime (Docker)
- Full debugging capabilities with breakpoints
- Step through code, inspect variables

## 🏗️ Architecture: How Everything Works Together

Understanding the debugging architecture helps troubleshoot issues and customize your setup.

### The Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Your Mac (Host Machine)                         │
│                                                                     │
│  ┌──────────────────────┐                                          │
│  │   Cursor Editor      │                                          │
│  │                      │                                          │
│  │  • Set breakpoints   │                                          │
│  │  • Press F5          │                                          │
│  │  • Inspect variables │                                          │
│  │  • Step through code │                                          │
│  └──────────┬───────────┘                                          │
│             │                                                       │
│             │ 1. Trigger: .vscode/tasks.json                       │
│             │    runs debug_sam.sh                                 │
│             ▼                                                       │
│  ┌──────────────────────┐                                          │
│  │   debug_sam.sh       │                                          │
│  │                      │                                          │
│  │  • Activate venv     │                                          │
│  │  • Kill port 5678    │                                          │
│  │  • sam build         │◄── Uses: Makefile                       │
│  │  • sam local invoke  │         infrastructure/template-debug   │
│  └──────────┬───────────┘                                          │
│             │                                                       │
│             │ 2. SAM starts Docker                                 │
│             ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │         Docker Container (Lambda Runtime)               │      │
│  │         Amazon Linux 2, Python 3.12                     │      │
│  │                                                         │      │
│  │  ┌───────────────────────────────────────────┐         │      │
│  │  │  lambda_function_debug.py                 │         │      │
│  │  │                                           │         │      │
│  │  │  1. Import debugpy                        │         │      │
│  │  │  2. debugpy.listen("0.0.0.0", 5678)      │         │      │
│  │  │     ↓ Opens port inside container         │         │      │
│  │  │  3. print("⏳ Waiting...")                │         │      │
│  │  │  4. debugpy.wait_for_client()            │         │      │
│  │  │     ↓ Pauses execution here               │         │      │
│  │  └───────────────────────────────────────────┘         │      │
│  │                        ▲                                │      │
│  │                        │ Port 5678 forwarded             │      │
│  │                        │ by Docker & SAM                 │      │
│  └────────────────────────┼─────────────────────────────────┘      │
│                           │                                        │
│  ┌────────────────────────┴─────────┐                             │
│  │   localhost:5678                 │                             │
│  │   (Port forwarding active)       │                             │
│  └────────────────────▲──────────────┘                             │
│                       │                                            │
│                       │ 3. Debug Adapter Protocol (DAP)            │
│                       │    Bidirectional communication             │
│  ┌────────────────────┴──────────────┐                             │
│  │   Cursor Debugger                 │                             │
│  │   (.vscode/launch.json)           │                             │
│  │                                   │                             │
│  │   • connect: localhost:5678       │                             │
│  │   • Send: breakpoints, commands   │                             │
│  │   • Receive: stack traces, vars   │                             │
│  └───────────────────────────────────┘                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Debug Flow (Step-by-Step)

#### **Step 1: You Press F5**

**What happens:**
- Cursor reads `.vscode/launch.json`
- Sees `"preLaunchTask": "Start SAM Local Debug"`
- Looks up that task in `.vscode/tasks.json`
- Executes: `./debug_sam.sh`

**Key Config:**
```json
// .vscode/launch.json
{
  "preLaunchTask": "Start SAM Local Debug",  // ← Runs before attaching
  "connect": {
    "host": "localhost",
    "port": 5678
  }
}
```

#### **Step 2: debug_sam.sh Executes**

**What the script does (line by line):**

```bash
# 1. Find script directory (works from any working directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Activate Python virtual environment (needed for sam, pip)
source "$SCRIPT_DIR/venv/bin/activate"

# 3. Kill any process using port 5678 (clean slate)
lsof -ti:5678 | xargs kill -9 2>/dev/null

# 4. Build Lambda (run Makefile)
sam build --template infrastructure/template-debug.yaml
```

**What SAM build does:**
- Reads `infrastructure/template-debug.yaml`
- Sees `BuildMethod: makefile`
- Runs `Makefile` target: `build-PriceTrackerScraperFunction`
- Installs from `requirements-dev.txt` with platform flags:
  - `--platform manylinux2014_x86_64` (Linux binaries, not Mac)
  - `--only-binary=:all:` (pre-built wheels only)
  - `--python-version 3.12` (match Lambda runtime)
- Copies files to `.aws-sam/build/PriceTrackerScraperFunction/`

**Why platform flags matter:**
Your Mac uses ARM64 or x86_64 macOS binaries. Lambda uses x86_64 Linux binaries. Packages like `psutil` and `lxml` have native code that's compiled differently for each platform. Without these flags, you'd install Mac binaries that fail in the Linux container.

```bash
# 5. Start SAM local invoke
sam local invoke PriceTrackerScraperFunction \
  --template .aws-sam/build/template.yaml \
  --event events/test_mercadolivre.json \
  --debug-port 5678
```

**What SAM local invoke does:**
1. Pulls/uses Docker image: `public.ecr.aws/lambda/python:3.12-rapid-x86_64`
2. Starts container with Lambda runtime
3. Mounts `.aws-sam/build/PriceTrackerScraperFunction/` as `/var/task` in container
4. Sets environment variables from template (including `DEBUG_PORT=5678`)
5. Exposes container port 5678 → host port 5678
6. Runs: `python -m awslambdaric lambda_function_debug.lambda_handler`

#### **Step 3: Lambda Runtime Starts (Inside Docker)**

**What happens in the container:**

1. **Python interpreter starts**
   ```python
   # Lambda runtime imports: lambda_function_debug.py
   ```

2. **Module-level code executes** (before function definition)
   ```python
   # lambda_function_debug.py lines 14-21
   if os.getenv('DEBUG_PORT'):  # ← DEBUG_PORT = '5678' from template
       import debugpy
       debug_port = int(os.getenv('DEBUG_PORT', 5678))
       debugpy.listen(("0.0.0.0", debug_port))  # ← Opens port INSIDE container
       print(f"⏳ Waiting for debugger to attach on port {debug_port}...")
       debugpy.wait_for_client()  # ← PAUSES HERE until debugger connects
   ```

3. **Output streams to your terminal**
   - You see: "⏳ Waiting for debugger to attach on port 5678..."
   - Execution is **frozen** at `debugpy.wait_for_client()`

**Why 0.0.0.0:**
- `0.0.0.0` means "listen on all network interfaces" inside the container
- Allows connections from outside the container (from your Mac)
- SAM's `--debug-port 5678` forwards container:5678 → localhost:5678

#### **Step 4: Task Detects Ready State**

**What `.vscode/tasks.json` does:**

```json
"problemMatcher": [{
  "background": {
    "beginsPattern": "Building Lambda",
    "endsPattern": "⏳ Waiting for debugger to attach on port 5678..."
  }
}]
```

- Watches terminal output from `debug_sam.sh`
- When it sees "⏳ Waiting for debugger..." → signals task is "ready"
- Cursor knows it's safe to try connecting

#### **Step 5: Debugger Attaches**

**What Cursor does:**

1. Reads connection config from `.vscode/launch.json`:
   ```json
   "connect": {
     "host": "localhost",  // Your Mac
     "port": 5678          // Forwarded to container
   }
   ```

2. Opens TCP connection to `localhost:5678`
3. Sends Debug Adapter Protocol (DAP) initialization
4. Sends breakpoint locations (file paths + line numbers)

**What debugpy does (inside container):**

1. `wait_for_client()` receives connection → unblocks!
2. Prints: "✅ Debugger attached!"
3. Maps breakpoint paths using `pathMappings`:
   ```json
   "pathMappings": [{
     "localRoot": "${workspaceFolder}",  // /Users/you/project
     "remoteRoot": "/var/task"            // Container path
   }]
   ```
4. Sets internal breakpoints at specified lines
5. Continues execution

**Path mapping example:**
- You set breakpoint at: `/Users/you/project/lambda_function.py:25`
- Debugpy translates to: `/var/task/lambda_function.py:25`
- That's where the file actually is inside the container!

#### **Step 6: Code Runs Until Breakpoint**

**What happens:**

1. `lambda_function_debug.lambda_handler(event, context)` is called
2. It delegates to: `lambda_function.lambda_handler(event, context)`
3. Your Lambda code executes normally
4. When execution reaches a line with a breakpoint:
   - Python interpreter pauses
   - debugpy sends "paused" event to Cursor
   - Cursor highlights the line and shows variables

#### **Step 7: You Debug Interactively**

**What you can do:**

- **Inspect variables**: Hover over variables, check Variables panel
- **Evaluate expressions**: Type in Debug Console (bottom panel)
  ```python
  len(html)
  price * 2
  soup.select('.price')
  ```
- **Step through code**:
  - F10: Step Over (run line, don't go into functions)
  - F11: Step Into (follow function calls)
  - Shift+F11: Step Out (finish current function)
  - F5: Continue (run until next breakpoint)
- **Modify execution**: Change variable values in Debug Console
- **Hot evaluation**: Test fixes without restarting

**Behind the scenes:**
- Every step command → DAP message to debugpy
- debugpy controls Python interpreter
- After each step → sends back stack trace + variables
- Cursor updates UI

#### **Step 8: Execution Completes**

**What happens:**

1. Your Lambda returns a response
2. SAM prints the response JSON
3. Lambda container stops (SAM terminates it)
4. Debug connection closes
5. Terminal shows "✅ SAM execution completed"

## 📝 Detailed Step-by-Step Instructions

### 2. Wait for Debug Message

You'll see:
```
⏳ Waiting for debugger to attach on port 5678...
```

**Don't continue until you see this message!**

### 3. Set Breakpoints

In Cursor/VS Code, click in the gutter (left of line numbers) to set breakpoints:

**Recommended breakpoint locations:**
- `lambda_function.py` line 83 - Where scraper is called
- `scrapers/mercadolivre.py` line 77 - After price extraction
- `scrapers/base.py` line 189 - Inside extract_price_from_html

### 4. Attach Debugger

- Press `F5` (or click Run and Debug icon)
- Select **"Attach to SAM Local (Debug)"** from the dropdown
- Debugger will connect

You'll see:
```
✅ Debugger attached!
```

### 5. Debug!

- Code execution continues
- Pauses at your breakpoints
- Use debug controls:
  - `F5` - Continue
  - `F10` - Step Over
  - `F11` - Step Into
  - `Shift+F11` - Step Out

---

## 🔍 Common Debugging Scenarios

### Inspect HTML Content

When paused at a breakpoint where `html` variable exists:

**In Debug Console (bottom panel):**
```python
# View first 500 characters
html[:500]

# Save to file for inspection
with open('debug_html.html', 'w', encoding='utf-8') as f: f.write(html)
```

Then open `debug_html.html` in your browser to see the actual HTML structure.

### Test Different CSS Selectors

```python
# In Debug Console:
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'lxml')

# Test selector
soup.select('span.andes-money-amount__fraction')

# Get text from element
[elem.get_text() for elem in soup.select('span.andes-money-amount__fraction')]
```

### Check Variables

- **Hover** over variables to see values
- **Add to Watch** panel for continuous monitoring
- **Use Debug Console** to evaluate expressions

---

## 🚨 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'debugpy'"

**Solution:**
```bash
pip install debugpy
# or
pip install -r requirements-dev.txt
```

### Issue: Port 5678 already in use

**Solution:**
```bash
# Kill existing process
lsof -ti:5678 | xargs kill -9

# Or change port in:
# - infrastructure/template-debug.yaml (DEBUG_PORT)
# - .vscode/launch.json (port)
# - debug_sam.sh (--debug-port)
```

### Issue: Debugger won't attach

**Solution:**
1. Make sure SAM shows "⏳ Waiting for debugger to attach..."
2. Try stopping SAM (Ctrl+C) and restarting
3. Check Docker is running
4. Verify `debugpy` is installed

### Issue: Breakpoints not hitting

**Solution:**
1. Verify you selected "Attach to SAM Local (Debug)" configuration
2. Check breakpoint is on an executable line (not comments/blank lines)
3. Make sure code hasn't been optimized away
4. Try `justMyCode: false` in launch.json (already set)

### Issue: SAM build fails

**Solution:**
```bash
# Check Python version
python --version  # Should be 3.12

# Clean build
rm -rf .aws-sam
sam build --template infrastructure/template-debug.yaml

# Check template syntax
sam validate --template infrastructure/template-debug.yaml
```

---

## 📝 Debugging Tips

### 1. Strategic Breakpoints

Set breakpoints at key decision points:
- Where data is fetched (HTTP requests)
- Where parsing happens (BeautifulSoup selectors)
- Where errors might occur (try/except blocks)

### 2. Use Debug Console

The Debug Console is powerful - you can:
- Run Python code in the current context
- Test functions with different inputs
- Inspect complex data structures

### 3. Conditional Breakpoints

Right-click a breakpoint → Edit Breakpoint → Add condition:
```python
price is None  # Only break when price is None
url.startswith('https://produto')  # Only break for certain URLs
```

### 4. Watch Expressions

Add expressions to Watch panel:
```python
len(html)
result.price
soup.select(selector)
```

### 5. Step Through Efficiently

- `F10` (Step Over) - Don't go into function details
- `F11` (Step Into) - Dive into function implementation
- Use both strategically to navigate code

---

## 🎬 Typical Debug Workflow

1. **Start debug session**
   ```bash
   ./debug_sam.sh
   ```

2. **Set initial breakpoint** where you think the issue is

3. **Attach debugger** (F5 → "Attach to SAM Local")

4. **Code pauses** at breakpoint

5. **Inspect variables** and understand state

6. **Step through code** to see what happens

7. **Try fixes** in Debug Console

8. **Stop debugging** (Shift+F5)

9. **Update code** with fix

10. **Test again** - repeat steps 1-8

---

## ⚠️ Important Notes

### Production vs Development

**DO NOT deploy these to production:**
- ❌ `lambda_function_debug.py` - Debug wrapper only
- ❌ `template-debug.yaml` - Debug configuration only
- ❌ `requirements-dev.txt` dependencies - Contains debugging/testing tools

**For production deployments:**
- ✅ Use `lambda_function.py` (clean production code)
- ✅ Use `template.yaml` (production SAM template)
- ✅ Use `requirements.txt` (production dependencies only)

### Requirements Files Explained

📦 **`requirements.txt`** (Production)
- Core Lambda dependencies only
- No debugging or testing tools
- Minimal package size for faster cold starts
- Used by production deployments

📦 **`requirements-dev.txt`** (Development & Debugging)
- Includes all production deps via `-r requirements.txt`
- Adds development tools: `debugpy`, `pytest`
- Adds testing tools: `testcontainers`, `docker`, `sqlalchemy`
- Used by SAM debug builds (Makefile references this)
- Extra packages don't affect Lambda execution

### Prerequisites

- 🐳 **Docker Desktop** must be running (SAM needs it for containers)
- 🐍 **Python virtual environment** activated (or `debug_sam.sh` activates it)
- 📦 **AWS SAM CLI** installed (`brew install aws-sam-cli`)

---

## 🆘 Deep Dive: Common Issues

### Issue: "ECONNREFUSED 127.0.0.1:5678"

**What it means:**
The debugger tried to connect to port 5678, but nothing was listening yet.

**Why it happens:**
Docker takes time to:
1. Start the container (~2-3 seconds)
2. Set up port forwarding (container:5678 → localhost:5678)
3. Start Python and run debugpy.listen()

The automatic task waits for the "⏳ Waiting for debugger..." message, but sometimes Docker's port forwarding isn't quite ready.

**Solutions:**
1. **Best**: Wait for task to detect ready state automatically (it should work)
2. If it fails: Press F5 again to retry (port is ready now)
3. Manual: Run `./debug_sam.sh` in terminal, wait 5 seconds after seeing "⏳", then F5

---

### Issue: "cannot import name '_psutil_linux'" or "lxml" errors

**What it means:**
You installed macOS binaries but Lambda needs Linux binaries.

**Why it happens:**
When you `pip install` on your Mac without platform flags, pip downloads packages compiled for macOS. Packages with native code (C extensions) like `psutil`, `lxml`, `psycopg2-binary` are platform-specific.

**The fix (already implemented):**
```makefile
# Makefile uses platform flags
pip install -r requirements-dev.txt \
    --platform manylinux2014_x86_64 \  # Linux x86_64
    --only-binary=:all: \               # Pre-built wheels
    --python-version 3.12 \             # Match Lambda
    --implementation cp                  # CPython
```

**How to verify it's working:**
```bash
sam build --template infrastructure/template-debug.yaml
# Check output for "Using cached psycopg2_binary-2.9.9-cp312-cp312-manylinux"
# Should say "manylinux" NOT "macosx"
```

---

### Issue: Port 5678 already in use

**What it means:**
Another process is using port 5678 (probably a previous SAM session that didn't stop cleanly).

**Quick fix:**
`debug_sam.sh` automatically kills port 5678 at startup:
```bash
lsof -ti:5678 | xargs kill -9 2>/dev/null || true
```

**Manual fix:**
```bash
# See what's using the port
lsof -i :5678

# Kill it
lsof -ti:5678 | xargs kill -9
```

---

### Issue: Breakpoints not hitting (gray dots instead of red)

**What it means:**
Debugger can't map your source files to the files in the container.

**Common causes:**

1. **Wrong path mappings**
   ```json
   // .vscode/launch.json should have:
   "pathMappings": [{
     "localRoot": "${workspaceFolder}",
     "remoteRoot": "/var/task"
   }]
   ```

2. **File not in build output**
   Check: `.aws-sam/build/PriceTrackerScraperFunction/`
   If your file isn't there, update `Makefile` to copy it.

3. **justMyCode filtering**
   If breakpoint is in a library file:
   ```json
   "justMyCode": false  // Set to false to debug libraries
   ```

4. **Breakpoint on non-executable line**
   Move breakpoint to a line with actual code (not comments, blank lines, or function signatures).

---

### Issue: "Docker container not starting"

**Diagnostic steps:**

1. **Check Docker is running**
   ```bash
   docker ps
   # Should show running containers or empty list (not error)
   ```

2. **Check Docker image**
   ```bash
   docker images | grep lambda
   # Should see: public.ecr.aws/lambda/python
   ```

3. **Test SAM without debug**
   ```bash
   sam local invoke PriceTrackerScraperFunction \
     --template .aws-sam/build/template.yaml \
     --event events/test_mercadolivre.json
   ```

4. **Check Docker resources**
   - Docker Desktop → Settings → Resources
   - Ensure sufficient CPU/Memory allocated
   - SAM needs at least 2GB RAM

---

### Issue: "Build takes forever" or "Downloading dependencies..."

**Why it's slow:**

First build after changing dependencies:
- Downloads all packages from PyPI
- Can take 2-3 minutes with cold cache

Subsequent builds:
- SAM caches dependencies
- Only rebuilds if `requirements-dev.txt` hash changes
- Should be ~10-20 seconds

**Speed it up:**

1. **Don't change dependencies often**
   - SAM caches based on requirements file hash
   - Any change = full rebuild

2. **Use local pip cache**
   ```bash
   export PIP_CACHE_DIR=$HOME/.cache/pip
   ```

3. **Pre-download in venv** (pip will reuse cache)
   ```bash
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

---

## 🆘 Getting Help

If you're still stuck after trying the above:

1. **Check terminal output** from `debug_sam.sh` for detailed error messages
2. **Verify Docker** is running: `docker ps`
3. **Test SAM without debug**: 
   ```bash
   sam local invoke --template .aws-sam/build/template.yaml \
     --event events/test_mercadolivre.json
   ```
4. **Check SAM logs** in terminal for Python tracebacks
5. **Validate template**:
   ```bash
   sam validate --template infrastructure/template-debug.yaml
   ```
6. **Clean rebuild**:
   ```bash
   rm -rf .aws-sam
   ./debug_sam.sh
   ```

---

## 📚 Additional Resources

- **AWS SAM Documentation**: https://docs.aws.amazon.com/serverless-application-model/
- **debugpy Documentation**: https://github.com/microsoft/debugpy
- **VS Code Python Debugging**: https://code.visualstudio.com/docs/python/debugging
- **Debug Adapter Protocol**: https://microsoft.github.io/debug-adapter-protocol/

---

## 🔖 Quick Reference

### File Locations

| File | Purpose | Deploy to Production? |
|------|---------|----------------------|
| `lambda_function.py` | Production Lambda code | ✅ Yes |
| `lambda_function_debug.py` | Debug wrapper | ❌ No |
| `requirements.txt` | Production dependencies | ✅ Yes |
| `requirements-dev.txt` | Dev/debug dependencies | ❌ No |
| `infrastructure/template.yaml` | Production SAM template | ✅ Yes |
| `infrastructure/template-debug.yaml` | Debug SAM template | ❌ No |
| `debug_sam.sh` | Debug automation script | ❌ No |
| `.vscode/launch.json` | Debugger configuration | ❌ No |
| `.vscode/tasks.json` | Task automation | ❌ No |

### Key Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **F5** | Start debugging / Continue |
| **F10** | Step Over (execute line, don't enter functions) |
| **F11** | Step Into (enter function calls) |
| **Shift+F11** | Step Out (finish current function) |
| **Shift+F5** | Stop debugging |
| **Cmd+Shift+D** | Open Debug view |

### Debug Commands (Debug Console)

```python
# Inspect variables
len(html)
type(price)
vars(result)

# Test code snippets
soup = BeautifulSoup(html, 'lxml')
soup.select('.price')

# Save data for analysis
with open('/tmp/debug.html', 'w') as f: f.write(html)

# Modify execution
price = 999.99  # Change variable value
```

### Important Ports

- **5678**: Debug port (debugpy listens here)
- Container:5678 → Docker port forwarding → localhost:5678 → Cursor debugger

### Common Commands

```bash
# Start debugging (manual)
./debug_sam.sh

# Clean rebuild
rm -rf .aws-sam && ./debug_sam.sh

# Kill port 5678
lsof -ti:5678 | xargs kill -9

# Check Docker
docker ps

# Validate SAM template
sam validate --template infrastructure/template-debug.yaml

# Test without debugging
sam local invoke PriceTrackerScraperFunction \
  --template .aws-sam/build/template.yaml \
  --event events/test_mercadolivre.json
```

### Environment Variables (Debug Template)

- `DEBUG_PORT=5678` - Enables debugpy in lambda_function_debug.py
- `DATABASE_URL` - Your database connection string
- `LOG_LEVEL=DEBUG` - Set logging verbosity

---

**Happy Debugging! 🐛🔍**
