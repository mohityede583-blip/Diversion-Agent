function triggerAIIncidentAnalysis() {
    // 1. Capture current form values (including unsaved draft text)
    var incNumber = g_form.getValue('number') || '';
    var shortDesc = g_form.getValue('short_description') || '';
    var description = g_form.getValue('description') || '';

    // Work Notes: Extract unsaved draft text entered by the user
    var workNotes = g_form.getValue('work_notes') || '';

    // Fallback for modern Next Experience / Workspace journal inputs if getValue is empty
    if (!workNotes) {
        var workNotesElem = document.getElementById('activity-stream-work_notes-textarea') ||
            document.getElementById('incident.work_notes');
        if (workNotesElem && workNotesElem.value) {
            workNotes = workNotesElem.value;
        }
    }

    // 2. Validate input before calling backend agent
    if (!shortDesc.trim() && !description.trim()) {
        g_form.showFieldMsg('short_description', 'Please enter a Short Description or Description before analyzing.', 'error');
        return;
    }

    // 3. User feedback message
    g_form.addInfoMessage('✨ Analyzing Incident ...');

    // 4. Construct payload with exact current field states
    var payload = {
        number: incNumber,
        short_description: shortDesc,
        description: description,
        work_notes: workNotes
    };

    // 5. POST to FastAPI Backend Agent
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'http://localhost:8000/api/incidents/analyse', true);
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                try {
                    var response = JSON.parse(xhr.responseText);
                    g_form.clearMessages();

                    showAIAnalysisModal(
                        response.incident_number || incNumber,
                        response.analysis,
                        response.matched_incidents
                    );
                } catch (e) {
                    g_form.addErrorMessage('Parse Error: ' + e.message);
                }
            } else {
                g_form.addErrorMessage('Server error (' + xhr.status + '). Ensure local FastAPI backend on port 8000 is running.');
            }
        }
    };

    xhr.send(JSON.stringify(payload));
}

function showAIAnalysisModal(incNumber, analysisText, matchedIncidents) {
    var doc = document;
    var existingModal = doc.getElementById('ai-analysis-modal-overlay');
    if (existingModal) existingModal.remove();

    var overlay = doc.createElement('div');
    overlay.id = 'ai-analysis-modal-overlay';
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(4px); z-index: 999999; display: flex; align-items: center; justify-content: center;';

    var card = doc.createElement('div');
    card.style.cssText = 'background: #ffffff; width: 800px; max-width: 92%; border-radius: 12px; padding: 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column; gap: 16px; font-family: "Source Sans Pro", -apple-system, sans-serif; max-height: 90vh; overflow-y: auto;';

    // Header
    var headerDiv = doc.createElement('div');
    headerDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px;';

    // var h3 = doc.createElement('h3');
    // h3.style.cssText = 'margin: 0; color: #0f172a; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 8px;';
    // h3.innerHTML = '✨ AI Incident Analysis: ' + (incNumber || 'Draft Incident');
    // headerDiv.appendChild(h3);


    card.appendChild(headerDiv);



    // Analysis Body
    var analysisLabel = doc.createElement('label');
    analysisLabel.style.cssText = 'font-size: 14px; font-weight: 600; color: #334155;';
    analysisLabel.innerText = 'Analysis:';
    card.appendChild(analysisLabel);

    var contentBox = doc.createElement('div');
    contentBox.style.cssText = 'width: 100%; min-height: 250px; padding: 16px; border: 1.5px solid #cbd5e1; border-radius: 8px; font-family: sans-serif; font-size: 14px; color: #1e293b; line-height: 1.6; background: #fafafa; box-sizing: border-box; white-space: pre-wrap; overflow-y: auto; max-height: 400px;';
    var safeText = analysisText || "No analysis details returned.";
    var formattedText = safeText
        .replace(/\*?\*?\s*Not\s+(?:an|a)?\s*HIP\s+Issue\s*\*?\*?/gi, '\n<div style="background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; padding: 8px 16px; border-radius: 8px; font-size: 16px; font-weight: 900; display: inline-block; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(3, 105, 161, 0.1);">Not an HIP Issue</div>\n')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    contentBox.innerHTML = formattedText;
    card.appendChild(contentBox);

    // Footer Actions
    var footer = doc.createElement('div');
    footer.style.cssText = 'display: flex; justify-content: flex-end; gap: 12px; border-top: 1px solid #f1f5f9; padding-top: 14px;';

    var copyBtn = doc.createElement('button');
    copyBtn.type = 'button';
    copyBtn.innerText = '📋 Copy to Work Notes';
    copyBtn.style.cssText = 'background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 9px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px;';
    copyBtn.onclick = function () {
        if (g_form && analysisText) {
            var currentNotes = g_form.getValue('work_notes') || '';
            var formattedNotes = '[AI Incident Analysis]\n' + analysisText.replace(/\*\*/g, '');
            g_form.setValue('work_notes', currentNotes ? currentNotes + '\n\n' + formattedNotes : formattedNotes);

            // Extract assignment group and set it
            var cleanText = analysisText.replace(/\*/g, '');
            var groupMatch = cleanText.match(/Recommended Assignment Group:\s*([^(]+)/i);
            if (groupMatch && groupMatch[1]) {
                var groupName = groupMatch[1].trim().replace(/\.$/, ''); // Remove trailing dot if present
                // setDisplayValue is best for reference fields, but we also fallback to setValue
                try {
                    g_form.setDisplayValue('assignment_group', groupName);
                } catch (e) {
                    g_form.setValue('assignment_group', groupName);
                }
            }

            g_form.addInfoMessage('Analysis copied and Assignment Group updated!');
        }
        overlay.remove(); // Close the modal
    };

    var closeBtn = doc.createElement('button');
    closeBtn.type = 'button';
    closeBtn.innerText = 'Close';
    closeBtn.style.cssText = 'background: #0284c7; color: #ffffff; border: none; padding: 9px 24px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px;';
    closeBtn.onclick = function () { overlay.remove(); };

    footer.appendChild(copyBtn);
    footer.appendChild(closeBtn);
    card.appendChild(footer);

    overlay.appendChild(card);
    doc.body.appendChild(overlay);
}