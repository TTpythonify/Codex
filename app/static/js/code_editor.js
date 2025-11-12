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

    // Attach Run Code button handler here
    const runCodeBtn = document.getElementById('runCodeBtn');
    if (runCodeBtn) {
        runCodeBtn.addEventListener('click', () => {
            const code = editorInstance.getValue();

            // Optional: show alert
            alert('Check console for code output!');
            console.log('Running code:');
            console.log(code);
        });
    }
});
