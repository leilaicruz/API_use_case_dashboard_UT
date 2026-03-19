# 1. Check your Python installation

Make sure you have **Python 3.10 or newer** installed.

Open a Unix terminal
(**Git Bash on Windows, Terminal on macOS or Linux**) and run:

```bash
python --version
```

or

```bash
python3 --version
```

---

# 2. Create a project folder

Create a new folder for the workshop project and move into it:

```bash
mkdir api-dashboard-workshop
cd api-dashboard-workshop
```

---

# 3. Create and activate a virtual environment

Inside the project folder, create a virtual environment:

```bash
python3 -m venv api-dashboard-env
```

Activate the environment:

### macOS / Linux

```bash
source api-dashboard-env/bin/activatels -a

```

### Windows (Git Bash)

```bash
source api-dashboard-env/Scripts/activate
```

After activation, your terminal should display something like:

```
(api-dashboard-env)
```

---

# 4. Install the required libraries

### 4.1 Create a requirements file

```bash
touch requirements.txt
```

### 4.2 Add the following libraries to the file

Open the file with any text editor and paste:

```
requests>=2.31
pandas>=2.0
streamlit>=1.30
python-dotenv>=1.0
pytest>=8.0
ruff>=0.4
python-dateutil>=2.8
```

### 4.3 Install the libraries

Run:

```bash
pip install -r requirements.txt
```

---

# 5. Verify that Streamlit works

Test that Streamlit was installed correctly:

```bash
streamlit hello
```

This should open a **demo Streamlit application in your browser**.

---

# 6. Install Git (if needed)

The deployment step of the workshop will require **Git** and a **GitHub account**.

Check whether Git is installed:

```bash
git --version
```

If Git is not installed, download it from:

[https://git-scm.com/](https://git-scm.com/)


