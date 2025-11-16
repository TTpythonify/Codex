require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.39.0/min/vs' } });

let editorInstance = null;
let terminal = null;

// Initialize xterm.js terminal first (before Monaco loads)
function initTerminal() {
    // Check if Terminal is available
    if (typeof Terminal === 'undefined') {
        console.error('xterm.js not loaded! Terminal constructor not found.');
        return;
    }

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

// Initialize Terminal immediately when script loads
initTerminal();

// Load Monaco Editor
require(['vs/editor/editor.main'], function () {
    // Create the editor
    editorInstance = monaco.editor.create(document.getElementById('editor'), {
        value: '# Write your Python code here\nprint("Hello, CODEX!")\n',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on'
    });

    // Attach Run Code button handler
    const runCodeBtn = document.getElementById('runCodeBtn');
    if (runCodeBtn) {
        runCodeBtn.addEventListener('click', runCode);
    }

    // Terminal controls
    document.getElementById('clearTerminal').addEventListener('click', () => {
        if (terminal) {
            terminal.clear();
            terminal.writeln('\x1b[1;36mCODEX Terminal\x1b[0m');
            terminal.writeln('Ready to execute code...\n');
        }
    });

    document.getElementById('closeTerminal').addEventListener('click', () => {
        const terminalPanel = document.querySelector('.terminal-panel');
        terminalPanel.classList.toggle('closed');
        // Trigger editor resize
        setTimeout(() => editorInstance.layout(), 100);
    });

    // Load initial file tree
    const repoId = document.getElementById('repoId').value;
    if (repoId) {
        loadFileTree(repoId);
    }
});

// ============================================================================
// FOLDER CREATION FUNCTIONALITY
// ============================================================================

// New Folder Button - Opens modal and loads existing folders
document.getElementById('newFolderBtn').addEventListener('click', async () => {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'flex';
    
    // Load existing folders into the dropdown
    const repoId = document.getElementById('repoId').value;
    await loadFoldersIntoDropdown(repoId);
});

// Close modal handlers
document.getElementById('closeFolderModal').addEventListener('click', () => {
    closeFolderModal();
});

document.getElementById('cancelFolderBtn').addEventListener('click', () => {
    closeFolderModal();
});

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    const modal = document.getElementById('createFolderModal');
    if (e.target === modal) {
        closeFolderModal();
    }
});

function closeFolderModal() {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'none';
    document.getElementById('newFolderName').value = '';
    document.getElementById('parentFolderSelect').innerHTML = '<option value="">📁 Root (top level)</option>';
}

// Load existing folders into dropdown
async function loadFoldersIntoDropdown(repoId) {
    try {
        const response = await fetch(`/get_files/${repoId}`);
        const data = await response.json();
        
        if (response.ok) {
            const dropdown = document.getElementById('parentFolderSelect');
            dropdown.innerHTML = '<option value="">📁 Root (top level)</option>';
            
            // Filter only folders from the files
            const folders = data.files.filter(f => f.type === 'folder');
            
            // Sort folders by path for better organization
            folders.sort((a, b) => a.path.localeCompare(b.path));
            
            // Add each folder as an option
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                
                // Add indentation based on folder depth for visual hierarchy
                const depth = (folder.path.match(/\//g) || []).length;
                const indent = '  '.repeat(depth);
                option.textContent = `${indent}📁 ${folder.path}`;
                
                dropdown.appendChild(option);
            });
            
            console.log(`Loaded ${folders.length} folders into dropdown`);
        }
    } catch (error) {
        console.error('Error loading folders:', error);
    }
}

// Create Folder Button - Sends request to backend
document.getElementById('createFolderBtn').addEventListener('click', async () => {
    const folderName = document.getElementById('newFolderName').value.trim();
    const parentId = document.getElementById('parentFolderSelect').value || null;
    
    if (!folderName) {
        alert('Please enter a folder name');
        return;
    }
    
    const repoId = document.getElementById('repoId').value;
    
    const requestBody = {
        repo_id: repoId,
        folder_name: folderName,
        parent_id: parentId  // null for root, or folder ID for nested
    };
    
    console.log('Creating folder with:', requestBody);
    
    try {
        const response = await fetch('/create_folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Folder "${folderName}" created successfully!`);
            closeFolderModal();
            
            // Refresh the file tree to show new folder
            loadFileTree(repoId);
            
        } else {
            alert(`Error: ${data.error || data.message || 'Failed to create folder'}`);
        }
        
    } catch (error) {
        console.error('Error creating folder:', error);
        alert('Failed to create folder. Please try again.');
    }
});


// ============================================================================
// FILE CREATION FUNCTIONALITY
// ============================================================================

// New File Button - Opens modal and loads existing folders
document.getElementById('newFileBtn').addEventListener('click', async () => {
    const modal = document.getElementById('createFileModal');
    modal.style.display = 'flex';
    
    // Load existing folders into the dropdown
    const repoId = document.getElementById('repoId').value;
    await loadFoldersIntoFileDropdown(repoId);
});

// Close file modal handlers
document.getElementById('closeFileModal').addEventListener('click', () => {
    closeFileModal();
});

document.getElementById('cancelFileBtn').addEventListener('click', () => {
    closeFileModal();
});

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    const fileModal = document.getElementById('createFileModal');
    if (e.target === fileModal) {
        closeFileModal();
    }
});

function closeFileModal() {
    const modal = document.getElementById('createFileModal');
    modal.style.display = 'none';
    document.getElementById('newFileName').value = '';
    document.getElementById('fileLanguage').value = 'python';
    document.getElementById('parentFileSelect').innerHTML = '<option value="">📁 Root (top level)</option>';
}

// Load existing folders into file creation dropdown
async function loadFoldersIntoFileDropdown(repoId) {
    try {
        const response = await fetch(`/get_files/${repoId}`);
        const data = await response.json();
        
        if (response.ok) {
            const dropdown = document.getElementById('parentFileSelect');
            dropdown.innerHTML = '<option value="">📁 Root (top level)</option>';
            
            // Filter only folders
            const folders = data.files.filter(f => f.type === 'folder');
            
            // Sort folders by path
            folders.sort((a, b) => a.path.localeCompare(b.path));
            
            // Add each folder as an option
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                
                // Add indentation based on folder depth
                const depth = (folder.path.match(/\//g) || []).length;
                const indent = '  '.repeat(depth);
                option.textContent = `${indent}📁 ${folder.path}`;
                
                dropdown.appendChild(option);
            });
            
            console.log(`Loaded ${folders.length} folders into file dropdown`);
        }
    } catch (error) {
        console.error('Error loading folders for file creation:', error);
    }
}

// Map language to file extension
function getFileExtension(language) {
    const extensionMap = {
        'python': '.py',
        'javascript': '.js',
        'java': '.java',
        'cpp': '.cpp',
        'c': '.c'
    };
    return extensionMap[language] || '';
}

// Create File Button - Sends request to backend
document.getElementById('createFileBtn').addEventListener('click', async () => {
    const fileName = document.getElementById('newFileName').value.trim();
    const language = document.getElementById('fileLanguage').value;
    const parentId = document.getElementById('parentFileSelect').value || null;
    
    if (!fileName) {
        alert('Please enter a file name');
        return;
    }
    
    // Add appropriate extension based on language
    const extension = getFileExtension(language);
    const fullFileName = fileName + extension;
    
    const repoId = document.getElementById('repoId').value;
    
    const requestBody = {
        repo_id: repoId,
        file_name: fullFileName,
        language: language,
        content: '',  // Start with empty content
        parent_id: parentId
    };
    
    console.log('Creating file with:', requestBody);
    
    try {
        const response = await fetch('/create_file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`File "${fullFileName}" created successfully!`);
            closeFileModal();
            
            // Refresh the file tree to show new file
            loadFileTree(repoId);
            
            // Open the new file in the editor
            if (editorInstance) {
                editorInstance.setValue('');
                monaco.editor.setModelLanguage(editorInstance.getModel(), language);
            }
            
        } else {
            alert(`Error: ${data.error || data.message || 'Failed to create file'}`);
        }
        
    } catch (error) {
        console.error('Error creating file:', error);
        alert('Failed to create file. Please try again.');
    }
});

// ============================================================================
// FILE TREE DISPLAY
// ============================================================================

// Load and display file tree
async function loadFileTree(repoId) {
    try {
        const response = await fetch(`/get_files/${repoId}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('Loaded files:', data.files);
            displayFileTree(data.files);
        } else {
            console.error('Error loading files:', data.error);
        }
    } catch (error) {
        console.error('Error loading file tree:', error);
    }
}

// Display file tree in the sidebar
function displayFileTree(items) {
    const fileTreeContainer = document.getElementById('fileTreeContainer');
    fileTreeContainer.innerHTML = '';
    
    if (items.length === 0) {
        fileTreeContainer.innerHTML = '<div style="padding: 10px; color: #888;">No files or folders yet. Create one to get started!</div>';
        return;
    }
    
    // Build a hierarchical structure
    const tree = buildTree(items);
    
    // Render the tree
    renderTree(tree, fileTreeContainer, 0);
}

// Build hierarchical tree structure from flat list
function buildTree(items) {
    const itemMap = {};
    const rootItems = [];
    
    // First pass: create map of all items
    items.forEach(item => {
        itemMap[item.id] = { ...item, children: [] };
    });
    
    // Second pass: build parent-child relationships
    items.forEach(item => {
        if (item.parent_id && itemMap[item.parent_id]) {
            // This item has a parent, add it to parent's children
            itemMap[item.parent_id].children.push(itemMap[item.id]);
        } else {
            // This is a root-level item
            rootItems.push(itemMap[item.id]);
        }
    });
    
    return rootItems;
}

// Recursively render tree
function renderTree(items, container, depth) {
    items.forEach(item => {
        const itemElement = createTreeItemElement(item, depth);
        container.appendChild(itemElement);
        
        // If item has children, render them recursively
        if (item.children && item.children.length > 0) {
            const childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            childContainer.style.display = 'none'; // Start collapsed
            renderTree(item.children, childContainer, depth + 1);
            container.appendChild(childContainer);
            
            // Toggle children on folder click
            itemElement.addEventListener('click', (e) => {
                e.stopPropagation();
                childContainer.style.display = childContainer.style.display === 'none' ? 'block' : 'none';
                itemElement.classList.toggle('expanded');
            });
        }
    });
}

// Create a single tree item element
function createTreeItemElement(item, depth) {
    const div = document.createElement('div');
    div.className = `file-tree-item ${item.type}`;
    div.style.paddingLeft = `${depth * 16 + 8}px`;
    
    if (item.type === 'folder') {
        div.innerHTML = `
            <svg class="tree-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.75 1A1.75 1.75 0 000 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0016 13.25v-8.5A1.75 1.75 0 0014.25 3H7.5a.25.25 0 01-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75z"/>
            </svg>
            <span>${item.name}</span>
        `;
    } else {
        div.innerHTML = `
            <svg class="tree-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
            </svg>
            <span>${item.name}</span>
        `;
        
        // Click handler for files - load content in editor
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            if (editorInstance && item.content !== undefined) {
                editorInstance.setValue(item.content || '');
                
                // Update language based on file extension
                if (item.language) {
                    monaco.editor.setModelLanguage(editorInstance.getModel(), item.language);
                }
            }
        });
    }
    
    return div;
}

// ============================================================================
// CODE EXECUTION
// ============================================================================

function runCode() {
    if (!editorInstance) {
        console.error('Editor not ready yet');
        return;
    }

    if (!terminal) {
        console.error('Terminal not initialized');
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