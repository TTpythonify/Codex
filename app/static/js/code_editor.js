require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.39.0/min/vs' } });

let editorInstance = null;
let terminal = null;

// Tab Management System
let openTabs = []; 
let activeTabId = null; 

// Initialize xterm.js terminal first (before Monaco loads)
function initTerminal() {
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
        value: `// Welcome to CODEX!
// Select a file from the explorer to start coding,
// or create a new file using the buttons above.
// Happy coding!`,

        language: 'javascript',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 4,
        insertSpaces: true,
        detectIndentation: true,
        readOnly: true  
    });

    editorInstance.onDidChangeModelContent(() => {
        if (activeTabId) {
            const tab = openTabs.find(t => t.id === activeTabId);
            if (tab) {
                tab.content = editorInstance.getValue();
                tab.isDirty = true;
                updateTabsUI();
            }
        }
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
        setTimeout(() => editorInstance.layout(), 100);
    });

    // Load initial file tree
    const repoId = document.getElementById('repoId').value;
    if (repoId) {
        loadFileTree(repoId);
    }
});

// ============================================================================
// TAB MANAGEMENT SYSTEM
// ============================================================================

function openFileInTab(file) {
    // Check if file is already open
    const existingTab = openTabs.find(tab => tab.id === file.id);
    
    if (existingTab) {
        // File already open, just switch to it
        switchToTab(existingTab.id);
    } else {
        // Create new tab
        const newTab = {
            id: file.id,
            name: file.name,
            path: file.path,
            language: file.language,
            content: file.content,
            isDirty: false
        };
        
        openTabs.push(newTab);
        activeTabId = newTab.id;
        
        // Update editor
        loadTabIntoEditor(newTab);
        updateTabsUI();
    }
}

function switchToTab(tabId) {
    const tab = openTabs.find(t => t.id === tabId);
    if (!tab) return;
    
    // Save current tab content before switching
    if (activeTabId && editorInstance) {
        const currentTab = openTabs.find(t => t.id === activeTabId);
        if (currentTab) {
            currentTab.content = editorInstance.getValue();
        }
    }
    
    activeTabId = tabId;
    loadTabIntoEditor(tab);
    updateTabsUI();
}

function loadTabIntoEditor(tab) {
    if (!editorInstance) return;

    // Enable editor typing when a file is opened
    editorInstance.setValue(tab.content || '');
    editorInstance.updateOptions({ readOnly: false });

    // Initialize terminal if it hasn't been created yet
    if (!terminal) {
        initTerminal();
    }

    // Show terminal panel
    const terminalPanel = document.querySelector('.terminal-panel');
    if (terminalPanel) {
        terminalPanel.style.display = 'flex'; // show panel
        terminalPanel.classList.remove('closed'); // remove "closed" class if present
    }

    // Map languages to Monaco
    const languageMap = {
        'python': 'python',
        'javascript': 'javascript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c'
    };

    const monacoLanguage = languageMap[tab.language] || 'plaintext';
    monaco.editor.setModelLanguage(editorInstance.getModel(), monacoLanguage);

    // Set language-specific indentation
    const model = editorInstance.getModel();
    switch(tab.language) {
        case 'python':
            model.updateOptions({ tabSize: 4, insertSpaces: true });
            break;
        case 'javascript':
            model.updateOptions({ tabSize: 2, insertSpaces: true });
            break;
        case 'java':
        case 'cpp':
        case 'c':
            model.updateOptions({ tabSize: 4, insertSpaces: true });
            break;
        default:
            model.updateOptions({ tabSize: 4, insertSpaces: true });
    }
}


function closeTab(tabId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const tabIndex = openTabs.findIndex(t => t.id === tabId);
    if (tabIndex === -1) return;
    
    const tab = openTabs[tabIndex];
    
    // Check if tab has unsaved changes
    if (tab.isDirty) {
        const confirmClose = confirm(`${tab.name} has unsaved changes. Close anyway?`);
        if (!confirmClose) return;
    }
    
    // Remove tab
    openTabs.splice(tabIndex, 1);
    
    // If closing active tab, switch to another
    if (activeTabId === tabId) {
        if (openTabs.length > 0) {
            const nextTab = openTabs[Math.min(tabIndex, openTabs.length - 1)];
            switchToTab(nextTab.id);
        } else {
            activeTabId = null;
            if (editorInstance) {
                editorInstance.setValue('// Select a file from the explorer to start coding');
                editorInstance.updateOptions({ readOnly: true }); 
            }
        }
    }
    
    updateTabsUI();
}

function updateTabsUI() {
    const tabsContainer = document.querySelector('.tabs-container');
    if (!tabsContainer) return;
    
    tabsContainer.innerHTML = '';
    
    openTabs.forEach(tab => {
        const tabElement = document.createElement('div');
        tabElement.className = `tab ${tab.id === activeTabId ? 'active' : ''}`;
        
        // File icon based on language
        const iconMap = {
            'python': '🐍',
            'javascript': '📜',
            'java': '☕',
            'cpp': '⚙️',
            'c': '🔧'
        };
        const icon = iconMap[tab.language] || '📄';
        
        tabElement.innerHTML = `
            <span class="tab-icon">${icon}</span>
            <span class="tab-name">${tab.name}${tab.isDirty ? ' •' : ''}</span>
            <button class="tab-close" data-tab-id="${tab.id}">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z"/>
                </svg>
            </button>
        `;
        
        tabElement.addEventListener('click', (e) => {
            if (!e.target.closest('.tab-close')) {
                switchToTab(tab.id);
            }
        });
        
        const closeBtn = tabElement.querySelector('.tab-close');
        closeBtn.addEventListener('click', (e) => closeTab(tab.id, e));
        
        tabsContainer.appendChild(tabElement);
    });
}

// ============================================================================
// FOLDER CREATION FUNCTIONALITY
// ============================================================================

document.getElementById('newFolderBtn').addEventListener('click', async () => {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'flex';
    
    const repoId = document.getElementById('repoId').value;
    await loadFoldersIntoDropdown(repoId);
});

document.getElementById('closeFolderModal').addEventListener('click', () => {
    closeFolderModal();
});

document.getElementById('cancelFolderBtn').addEventListener('click', () => {
    closeFolderModal();
});

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

async function loadFoldersIntoDropdown(repoId) {
    try {
        const response = await fetch(`/get_files/${repoId}`);
        const data = await response.json();
        
        if (response.ok) {
            const dropdown = document.getElementById('parentFolderSelect');
            dropdown.innerHTML = '<option value="">📁 Root (top level)</option>';
            
            const folders = data.files.filter(f => f.type === 'folder');
            folders.sort((a, b) => a.path.localeCompare(b.path));
            
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                
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
        parent_id: parentId
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

document.getElementById('newFileBtn').addEventListener('click', async () => {
    const modal = document.getElementById('createFileModal');
    modal.style.display = 'flex';
    
    const repoId = document.getElementById('repoId').value;
    await loadFoldersIntoFileDropdown(repoId);
});

document.getElementById('closeFileModal').addEventListener('click', () => {
    closeFileModal();
});

document.getElementById('cancelFileBtn').addEventListener('click', () => {
    closeFileModal();
});

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

async function loadFoldersIntoFileDropdown(repoId) {
    try {
        const response = await fetch(`/get_files/${repoId}`);
        const data = await response.json();
        
        if (response.ok) {
            const dropdown = document.getElementById('parentFileSelect');
            dropdown.innerHTML = '<option value="">📁 Root (top level)</option>';
            
            const folders = data.files.filter(f => f.type === 'folder');
            folders.sort((a, b) => a.path.localeCompare(b.path));
            
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.id;
                
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

document.getElementById('createFileBtn').addEventListener('click', async () => {
    const fileName = document.getElementById('newFileName').value.trim();
    const language = document.getElementById('fileLanguage').value;
    const parentId = document.getElementById('parentFileSelect').value || null;
    
    if (!fileName) {
        alert('Please enter a file name');
        return;
    }
    
    const extension = getFileExtension(language);
    const fullFileName = fileName + extension;
    
    const repoId = document.getElementById('repoId').value;
    
    const requestBody = {
        repo_id: repoId,
        file_name: fullFileName,
        language: language,
        content: '',
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
            
            // Refresh file tree
            await loadFileTree(repoId);
            
            // Open the newly created file in a tab
            const newFile = {
                id: data.file.id,
                name: data.file.name,
                path: data.file.path,
                language: data.file.language,
                content: data.file.content || ''
            };
            openFileInTab(newFile);
            
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

function displayFileTree(items) {
    const fileTreeContainer = document.getElementById('fileTreeContainer');
    fileTreeContainer.innerHTML = '';
    
    if (items.length === 0) {
        fileTreeContainer.innerHTML = '<div style="padding: 10px; color: #888;">No files or folders yet. Create one to get started!</div>';
        return;
    }
    
    const tree = buildTree(items);
    renderTree(tree, fileTreeContainer, 0);
}

function buildTree(items) {
    const itemMap = {};
    const rootItems = [];
    
    items.forEach(item => {
        itemMap[item.id] = { ...item, children: [] };
    });
    
    items.forEach(item => {
        if (item.parent_id && itemMap[item.parent_id]) {
            itemMap[item.parent_id].children.push(itemMap[item.id]);
        } else {
            rootItems.push(itemMap[item.id]);
        }
    });
    
    return rootItems;
}

function renderTree(items, container, depth) {
    items.forEach(item => {
        const itemElement = createTreeItemElement(item, depth);
        container.appendChild(itemElement);
        
        if (item.children && item.children.length > 0) {
            const childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            childContainer.style.display = 'none';
            renderTree(item.children, childContainer, depth + 1);
            container.appendChild(childContainer);
            
            itemElement.addEventListener('click', (e) => {
                if (item.type === 'folder') {
                    e.stopPropagation();
                    childContainer.style.display = childContainer.style.display === 'none' ? 'block' : 'none';
                    itemElement.classList.toggle('expanded');
                }
            });
        }
    });
}

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
        
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            openFileInTab(item);
        });
    }
    
    return div;
}

// ============================================================================
// CODE EXECUTION - MULTI-LANGUAGE SUPPORT
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

    // Get the current language from the active tab
    let currentLanguage = 'python'; // Default
    if (activeTabId) {
        const activeTab = openTabs.find(t => t.id === activeTabId);
        if (activeTab) {
            currentLanguage = activeTab.language;
        }
    }



    const languageNames = {
        'python': 'Python',
        'javascript': 'JavaScript',
        'java': 'Java',
        'cpp': 'C++',
        'c': 'C'
    };

    terminal.writeln(`\x1b[1;36m▶ Running ${languageNames[currentLanguage] || 'code'}...\x1b[0m`);
    terminal.writeln('─'.repeat(50));

    fetch('/run_code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            code: code,
            language: currentLanguage,
            file_id:activeTabId

        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            terminal.writeln(`\x1b[1;31m✖ Error:\x1b[0m ${data.error}`);
        } else {
            const output = data.output || 'No output';
            const lines = output.split('\n');
            lines.forEach(line => {
                terminal.writeln(line);
            });
            
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