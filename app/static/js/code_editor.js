require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.39.0/min/vs' }});

// Load Monaco Editor
require(['vs/editor/editor.main'], function () {
    monaco.editor.create(document.getElementById('editor'), {
        value: '',           
        language: 'python',    
        theme: 'vs-dark',     
        automaticLayout: true  
    });
});
