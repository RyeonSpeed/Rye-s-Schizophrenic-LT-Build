# How to generate an Android APK for your project

## Initial Setup
1. Modify the existing `buildozer.spec` and `.android.json` files with the correct information for your project
2. A `main.py` python file is included in this branch. It will be the entry point for your compiled APK for android. Make sure it points to your project `my_special_project.ltproj` instead of `testing_proj.ltproj`

# Compilation
This process can only be done on Linux or MacOS, not Windows. 

Feel free to follow along to this video as well: https://www.youtube.com/watch?v=L6XOqakZOeA. It has a pretty good explanation of the steps required for generation of the APK.

## Installation of dependencies
Since you can only compile on Linux/MacOS, make sure you have one of those systems. If you are using Windows 11 or newer versions of Windows 10, you can use the Windows Subsystem for Linux, or WSL, which creates a virtual Linux machine on your Windows machine. It works pretty well!

https://learn.microsoft.com/en-us/windows/wsl/setup/environment

I installed the default Ubuntu distribution myself. I was able to run `wsl --install` from PowerShell and then restart (with updates) my machine. If you are running into issues, check that both WSL and Virtual Machine Platform are enabled by typing `Windows Features` into your start menu, clicking the `Turn Windows features on or off`, and then making sure those two features are checked. You can try unchecking them, restarting, and then checking them and restarting to see if that fixes your issues.

Once you have a Linux environment, make sure you have a recent version of Python, ideally Python 3.10+ as the default Python in your environment. You can type `python --version` to find the version.

The following instructions are modified from here: https://buildozer.readthedocs.io/en/latest/installation.html

1. Run `sudo apt update`
2. Run `sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev`
3. Clone lt-maker onto your system: `git clone https://gitlab.com/rainlash/lt-maker`
4. Navigate to the lt-maker directory
5. Run `pip3 install -r requirements_engine.txt`. This installs pygame and its dependencies.
6. Run `pip3 install buildozer`. This installs buildozer, which is the application that will take your Python code and convert it to an Android APK.
7. Run `pip3 install Cython==0.29.33`. Cython is also needed for the buildozer process.
8. Open your `~/.bashrc` file and add the following line at the end: `export PATH=$PATH:~/.local/bin`. This makes buildozer and other applications accessible to buildozer itself.

## Building

Since you already have a `buildozer.spec` file, you don't need to run `buildozer init`

From your lt-maker directory (make sure your project folder is also within the lt-maker directory), run `buildozer -v android debug`.

Expect to wait more than an hour the first time this happens, since it is doing a lot of one time compilation. Subsequent builds should be much faster.

If all goes well, you now have an Android .apk in your `bin` directory.
