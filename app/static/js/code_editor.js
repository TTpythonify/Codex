require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.39.0/min/vs' } });

let editorInstance = null;
let terminal = null;

// Load Monaco Editor
require(['vs/editor/editor.main'], function () {
    // Create the editor
    editorInstance = monaco.editor.create(document.getElementById('editor'), {
        value: '',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on'
    });

    // Initialize xterm.js terminal
    initTerminal();

    // Attach Run Code button handler
    const runCodeBtn = document.getElementById('runCodeBtn');
    if (runCodeBtn) {
        runCodeBtn.addEventListener('click', runCode);
    }

    // Terminal controls
    document.getElementById('clearTerminal').addEventListener('click', () => {
        if (terminal) {
            terminal.clear();
        }
    });

    document.getElementById('closeTerminal').addEventListener('click', () => {
        const terminalPanel = document.querySelector('.terminal-panel');
        terminalPanel.classList.toggle('closed');
        // Trigger editor resize
        setTimeout(() => editorInstance.layout(), 100);
    });
});

function initTerminal() {
    terminal = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Consolas, "Courier New", monospace',
        theme: {
            background: '#0d1117',
            foreground: '#c9d1d9',
            cursor: '#58a6ff',
            black: '#0d1117',
            red: '#ff6b6b',
            green: '#56d364',
            yellow: '#f0c674',
            blue: '#58a6ff',
            magenta: '#bc8cff',
            cyan: '#76e3ea',
            white: '#c9d1d9',
            brightBlack: '#484f58',
            brightRed: '#ff8585',
            brightGreen: '#7ee787',
            brightYellow: '#f8e3a1',
            brightBlue: '#79c0ff',
            brightMagenta: '#d2a8ff',
            brightCyan: '#b3f6ff',
            brightWhite: '#f0f6fc'
        },
        rows: 10,
        scrollback: 1000
    });

    terminal.open(document.getElementById('terminal'));
    terminal.writeln('\x1b[1;36mCODEX Terminal\x1b[0m');
    terminal.writeln('Ready to execute code...\n');
}

function runCode() {
    if (!editorInstance) {
        console.log('Editor not ready yet');
        return;
    }

    const code = editorInstance.getValue();
    
    if (!code.trim()) {
        terminal.writeln('\x1b[1;33m⚠ No code to execute\x1b[0m\n');
        return;
    }

    terminal.writeln('\x1b[1;32m▶ Running code...\x1b[0m');
    terminal.writeln('─'.repeat(50));

    fetch('/run_code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            terminal.writeln(`\x1b[1;31m✖ Error:\x1b[0m ${data.error}`);
        } else {
            // Write output line by line for better formatting
            const output = data.output || 'No output';
            const lines = output.split('\n');
            lines.forEach(line => {
                terminal.writeln(line);
            });
            
            // Show success/failure indicator
            if (data.success !== false) {
                terminal.writeln('\x1b[1;32m✓ Execution completed successfully\x1b[0m');
            } else {
                terminal.writeln('\x1b[1;31m✖ Execution failed\x1b[0m');
            }
        }
        terminal.writeln('─'.repeat(50) + '\n');
    })
    .catch(err => {
        terminal.writeln(`\x1b[1;31m✖ Error: ${err.message}\x1b[0m`);
        terminal.writeln('─'.repeat(50) + '\n');
        console.error('Error sending code:', err);
    });
}