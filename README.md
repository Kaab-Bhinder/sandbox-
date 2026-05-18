# Secure Sandbox Executor

A secure, isolated environment for executing Python code with resource limitations, security constraints, and a modern graphical user interface.

## Features

- **Isolated Execution Environment**: Run untrusted Python code safely without affecting the host system
- **Resource Limits**: 
  - CPU usage monitoring and limiting
  - Memory consumption constraints
  - Customizable timeout settings
- **Security Filtering**: Blocks dangerous operations like file system access, network connections, and system calls
- **Virtual File System**: Simulated file system for safe I/O operations
- **Process Monitoring**: Real-time tracking of sandbox process health and resource usage
- **Modern GUI**: Futuristic dark theme interface built with customtkinter
- **File Management**: Save/load Python scripts and virtual file system configurations
- **Execution Logs**: Comprehensive logging of all execution events

## System Requirements

- Python 3.8+
- Linux/Unix-based system (tested on Linux)
- Required Python libraries:
  - `customtkinter` - Modern GUI framework
  - `psutil` - System and process utilities

## Installation

1. **Clone or download the project**:
   ```bash
   cd SecureSandboxProject
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install customtkinter psutil
   ```

## Quick Start

Run the application:
```bash
python gui.py
```

The GUI will launch with a futuristic dark theme interface.

## Usage

### Basic Workflow

1. **Write or Load Code**: Enter Python code directly or load an existing script
2. **Configure Sandbox Settings**:
   - Adjust timeout (seconds)
   - Set memory limit percentage
   - Set CPU limit percentage
3. **Execute**: Click the execute button to run the code in the sandbox
4. **Review Results**: Check output, stderr, and execution logs
5. **Manage Files**: Save scripts and virtual file system configurations

### Virtual File System

The sandbox includes a simulated file system with default paths:
- `/sandbox/input.txt` - Input file
- `/sandbox/output.txt` - Output file

You can manage the VFS through the GUI and export/import configurations as JSON.

### Security

The sandbox blocks the following dangerous operations:
- `import os`, `import sys`, `import subprocess`, `import socket`
- Direct file operations with `open()`
- Code evaluation with `eval()`, `exec()`, `compile()`
- Module imports with `__import__`
- System utilities like `shutil`, `ctypes`, `pickle`
- Direct access to `os.*`, `sys.*`, `subprocess.*`

## Project Structure

```
SecureSandboxProject/
├── gui.py              # Main GUI application using customtkinter
├── sandbox.py          # Core sandbox controller and security logic
├── secure_exec.py      # Subprocess execution and resource monitoring
├── utils.py            # File I/O and dialog utilities
└── README.md           # This file
```

### Core Components

- **SandboxController** (`sandbox.py`): Main orchestrator for sandbox operations
  - Manages virtual file system
  - Enforces security policies
  - Maintains execution logs
  
- **SandboxRunner** (`secure_exec.py`): Handles subprocess execution
  - Monitors CPU and memory usage
  - Enforces timeout constraints
  - Safely terminates processes

- **FuturisticApp** (`gui.py`): User interface
  - Code editor and output display
  - System monitoring dashboard
  - File management interface

## Configuration

### Sandbox Defaults

- **Timeout**: 4 seconds
- **Memory Limit**: 25% of system RAM
- **CPU Limit**: 80% of CPU capacity

These can be adjusted through the GUI.

## Security Considerations

⚠️ **Important**: While this sandbox provides basic security measures, it is designed for preventing accidental harmful operations. For production use with truly untrusted code:

1. Consider running in a container (Docker)
2. Implement additional system-level restrictions
3. Use operating system-level sandboxing features
4. Monitor resource usage carefully

## Troubleshooting

### Module Import Errors
If you get `ModuleNotFoundError` for `customtkinter`, ensure it's installed:
```bash
pip install --upgrade customtkinter
```

### Process Not Terminating
If a sandbox process hangs, the application provides a "Force Kill" option to terminate it.

### Memory/CPU Limits Not Working
Verify that `psutil` is properly installed and you have appropriate system permissions to monitor processes.

## License

[Add your license here]

## Contributing

Contributions are welcome! Please ensure code follows the existing style and includes appropriate comments.

## Author

[Your name/organization]

## Changelog

### Version 1.0
- Initial release with core sandbox functionality
- GUI implementation with modern theme
- Resource monitoring and limits
- Virtual file system support
