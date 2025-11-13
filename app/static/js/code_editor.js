require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.39.0/min/vs' } });

let editorInstance = null;

// Load Monaco Editor
require(['vs/editor/editor.main'], function () {
    // Create the editor
    editorInstance = monaco.editor.create(document.getElementById('editor'), {
        value: '',              // Start with a blank page
        language: 'python',     // Python language
        theme: 'vs-dark',       // Dark theme
        automaticLayout: true,  // Auto-resize with container
        fontSize: 14,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on'
    });

    // Attach Run Code button handler
    const runCodeBtn = document.getElementById('runCodeBtn');
    if (runCodeBtn) {
        runCodeBtn.addEventListener('click', () => {
            if (!editorInstance) {
                console.log('Editor not ready yet');
                return;
            }

            const code = editorInstance.getValue();
            console.log('Sending code to backend:\n', code);

            fetch('/run_code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            })
            .then(response => response.json())
            .then(data => {
                console.log('=== Code Output ===\n', data.output);
            })
            .catch(err => console.error('Error sending code:', err));
        });
    }



});
