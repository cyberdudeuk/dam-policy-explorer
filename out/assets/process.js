/* How a return is processed: the team's proposed design, drawn from one set of data.
   The map, the workflows, the decision trees and the text version all read PROCESS, so they cannot disagree.
   Status: proposed. Source: the team's design notes, November 2026 (see docs/sources.md). */
(function (root) {
  'use strict';

  var PROCESS = {
    status: 'Proposed design, not yet built',
    // the five stages leaders see
    stages: [
      {id: 'collect', icon: 'i-inbox', title: 'Collect', text: 'Organisations send their returns. We keep each original file exactly as it arrived.'},
      {id: 'assure', icon: 'i-shield', title: 'Assure', text: 'We check every return. Where something needs correcting, we ask the organisation to correct it.'},
      {id: 'consolidate', icon: 'i-database', title: 'Consolidate', text: 'Accepted returns go into one cross-government register of critical data assets.'},
      {id: 'understand', icon: 'i-chart', title: 'Understand', text: 'Quick measures first, then a fuller dashboard, show where things stand.'},
      {id: 'act', icon: 'i-target', title: 'Act', text: 'We use what we learn to decide where support is needed most.'}
    ],
    // the eight swimlanes: who or what does the work
    lanes: [
      {id: 'L1', title: 'Organisation sending the return', who: 'The organisation’s coordinator', kind: 'human', icon: 'i-building'},
      {id: 'L2', title: 'Team mailbox', who: 'The team’s shared mailbox (Outlook)', kind: 'auto', icon: 'i-mail'},
      {id: 'L3', title: 'Receiving and logging', who: 'Automated (Power Automate)', kind: 'auto', icon: 'i-gear'},
      {id: 'L4', title: 'Safe storage', who: 'A restricted SharePoint library', kind: 'store', icon: 'i-folder'},
      {id: 'L5', title: 'Checking', who: 'Automated (Power Automate and Office Scripts)', kind: 'auto', icon: 'i-check'},
      {id: 'L6', title: 'Review and questions', who: 'The GDS team', kind: 'human', icon: 'i-people'},
      {id: 'L7', title: 'The register', who: 'The cross-government register of critical data assets', kind: 'register', icon: 'i-database'},
      {id: 'L8', title: 'Measures and action', who: 'Quick measures and the analytics dashboard', kind: 'insight', icon: 'i-chart'}
    ],
    // shapes: id, lane, row (top to bottom), label, type, workflow, what it does
    nodes: [
      {id: 'P01', lane: 'L1', row: 0, type: 'step', label: 'Fill in the Baseline Return', wf: '', text: 'The organisation fills in the Baseline Return workbook (version 3). The Baseline Return is the first list of critical data assets each organisation sends.'},
      {id: 'P02', lane: 'L1', row: 1, type: 'step', label: 'Send the return', wf: '', text: 'The organisation emails the finished workbook to the team’s shared mailbox.'},
      {id: 'P03', lane: 'L2', row: 2, type: 'step', label: 'Email and workbook arrive', wf: 'WF01', text: 'The email and its attached workbook (an XLSX file) arrive in the shared mailbox.'},
      {id: 'P04', lane: 'L3', row: 3, type: 'step', label: 'Give it a reference number', wf: 'WF01', text: 'Each return gets its own submission reference, with the sender, the time it arrived and the email’s ID.'},
      {id: 'P05', lane: 'L3', row: 4, type: 'step', label: 'Keep the original', wf: 'WF02', text: 'The original file is saved exactly as it arrived. Nobody changes it.'},
      {id: 'DS01', lane: 'L4', row: 5, type: 'store', label: 'Restricted library', wf: 'WF02', text: 'Originals are kept in a restricted SharePoint library (Microsoft’s shared document store).'},
      {id: 'P06', lane: 'L3', row: 6, type: 'step', label: 'Record the details', wf: 'WF02', text: 'The return’s details are recorded and its status is set to “received”.'},
      {id: 'SP01', lane: 'L5', row: 7, type: 'sub', label: 'Check the workbook', wf: 'WF03', text: 'Checks that the file opens, is the approved version 3 and has the expected layout.'},
      {id: 'D01', lane: 'L5', row: 8, type: 'decision', label: 'Is the workbook valid?', wf: 'WF03', text: 'Is this the approved version 3 workbook, laid out as expected?'},
      {id: 'SP02', lane: 'L5', row: 9, type: 'sub', label: 'Check each asset', wf: 'WF04', text: 'Checks every asset in the return: required details, allowed answers, purposes and links between answers.'},
      {id: 'D02', lane: 'L5', row: 10, type: 'decision', label: 'Anything blocking or unclear?', wf: 'WF04', text: 'Is there a mistake, or something unclear, that stops us using the return?'},
      {id: 'P07', lane: 'L6', row: 9, type: 'error', label: 'Log the issue', wf: '', text: 'The issue is written in the checking log, so nothing is lost.'},
      {id: 'P08', lane: 'L6', row: 10, type: 'step', label: 'A person reviews it', wf: '', text: 'A team member looks at the issue and decides what to do.'},
      {id: 'D03', lane: 'L6', row: 11, type: 'decision', label: 'Does it need correcting?', wf: '', text: 'Does the organisation need to change something, or can we accept it as it is?'},
      {id: 'P09', lane: 'L6', row: 12, type: 'error', label: 'Ask for a correction', wf: '', text: 'We email the coordinator to ask for a correction. They send a corrected return, which starts again at the mailbox.'},
      {id: 'P10', lane: 'L6', row: 13, type: 'accept', label: 'Accept the return', wf: '', text: 'The return is accepted. We keep the original, the checked version, the checking log and our decision.'},
      {id: 'SP03', lane: 'L7', row: 14, type: 'sub', label: 'Add to the register', wf: 'WF05', text: 'Each accepted asset is added to the register, or updates its earlier entry, keeping a record of where it came from.'},
      {id: 'DS02', lane: 'L7', row: 15, type: 'register', label: 'The register', wf: 'WF05', text: 'One managed register of critical data assets across government. Every entry shows where it came from.'},
      {id: 'SP04', lane: 'L8', row: 16, type: 'sub', label: 'Work out quick measures', wf: 'WF06', text: 'Quick measures from the register, available straight away.', col: 0},
      {id: 'SP05', lane: 'L8', row: 16, type: 'sub', label: 'Update the dashboard', wf: 'WF07', text: 'Updates the fuller analysis behind the dashboard.', col: 1},
      {id: 'O01', lane: 'L8', row: 17, type: 'output', label: 'Quick measures', wf: 'WF06', text: 'For example: how many assets, and how many have an owner, a steward and a quality plan.', col: 0},
      {id: 'O02', lane: 'L8', row: 17, type: 'output', label: 'Dashboard', wf: 'WF07', text: 'Views for senior leaders and for each department.', col: 1},
      {id: 'P11', lane: 'L8', row: 18, type: 'step', label: 'Decide where to help', wf: '', text: 'Find where the policy is not yet met, who needs most support and what patterns there are across government.'}
    ],
    // connectors, exactly as in the design notes
    edges: [
      ['P01', 'P02'], ['P02', 'P03'], ['P03', 'P04'], ['P04', 'P05'], ['P05', 'DS01'], ['DS01', 'P06'], ['P06', 'SP01'], ['SP01', 'D01'],
      ['D01', 'SP02', 'Yes'], ['D01', 'P07', 'No'], ['SP02', 'D02'], ['D02', 'P07', 'Yes'], ['D02', 'P10', 'No'],
      ['P07', 'P08'], ['P08', 'D03'], ['D03', 'P09', 'Yes'], ['D03', 'P10', 'No'], ['P09', 'P03', 'Corrected return'],
      ['P10', 'SP03'], ['SP03', 'DS02'], ['DS02', 'SP04'], ['DS02', 'SP05'], ['SP04', 'O01'], ['SP05', 'O02'], ['O01', 'P11'], ['O02', 'P11']
    ],
    workflows: [
      {id: 'WF01', icon: 'i-inbox', title: 'Receive the return', lane: 'L3', tech: 'Outlook shared mailbox and Power Automate',
        steps: ['An email arrives in the shared mailbox', 'Is it a data asset return?', 'Is a workbook (XLSX file) attached?', 'Record the email’s ID, the sender and the time it arrived', 'Give the return a submission reference'],
        makes: 'A submission record'},
      {id: 'WF02', icon: 'i-folder', title: 'Keep the original and record it', lane: 'L4', tech: 'Power Automate and a restricted SharePoint library',
        steps: ['Save the original file exactly as it arrived', 'Store it in the restricted library', 'Record its details', 'Set its status to “received”'],
        makes: 'The original, kept safe, and its record'},
      {id: 'WF03', icon: 'i-check', title: 'Check the workbook', lane: 'L5', tech: 'Power Automate and Office Scripts',
        steps: ['Does the file open?', 'Is it the approved version 3 workbook?', 'Is the layout as expected?', 'Are all the required columns there?', 'Has the worked example been removed?', 'Has anything else in the layout been changed?'],
        makes: 'Pass, or an issue for the team to review'},
      {id: 'WF04', icon: 'i-list', title: 'Check each asset', lane: 'L5', tech: 'Power Automate and Office Scripts',
        steps: ['For each asset in the return', 'Are the required details filled in?', 'Are the answers from the allowed lists?', 'Check the answers on the seven critical purposes', 'Do linked answers agree with each other?', 'Is the asset’s identity clear?', 'Record its position on owner, steward, catalogue, being findable, quality plan, sharing, classification, origin and location data'],
        makes: 'For each asset: pass, policy gap or error'},
      {id: 'WF05', icon: 'i-database', title: 'Add to the register', lane: 'L7', tech: 'The register workbook',
        steps: ['Take the accepted assets from the return', 'Match the organisation to its register reference', 'Match each asset to its lasting asset reference', 'Is it new? Add it. Is this a new return or version? Update it', 'Keep the record of its source, its checks and our decision'],
        makes: 'An up-to-date register entry for each asset'},
      {id: 'WF06', icon: 'i-chart', title: 'Work out quick measures', lane: 'L8', tech: 'Excel',
        steps: ['Number of critical data assets', 'Share with a data quality plan or equivalent', 'Share with an owner', 'Share with a steward', 'Share in a data catalogue', 'Share that can be found by others', 'Sharing between organisations', 'Purposes served', 'Where each return has got to'],
        makes: 'Quick measures, before the full dashboard is needed'},
      {id: 'WF07', icon: 'i-dashboard', title: 'Update the dashboard', lane: 'L8', tech: 'The analytics dashboard for the Data Asset Management (DAM) Policy',
        steps: ['Senior leaders’ view: overall standards, purposes, sharing and how many organisations have replied', 'Department view: quality plans, sharing, assets by purpose, gaps against the standards and priorities'],
        makes: 'A view of where things stand, to decide where to help'}
    ],
    decisions: [
      {id: 'D01', title: 'Is the workbook valid?', q: 'Is this the approved version 3 workbook, laid out as expected?',
        branches: [['Yes', 'Go on to check each asset (WF04)', 'good'], ['No', 'Log the issue and pass it to a person to review', 'bad']]},
      {id: 'D02', title: 'Is anything blocking or unclear?', q: 'After checking each asset: is there a mistake, or something unclear, that stops us using the return?',
        branches: [['No', 'Accept the return', 'good'], ['Yes', 'Log the issue and pass it to a person to review', 'bad']]},
      {id: 'D03', title: 'Does it need correcting?', q: 'Having looked at the issue: does the organisation need to change something?',
        branches: [['No', 'Accept the return as it is', 'good'], ['Yes', 'Email the coordinator to ask for a correction. The corrected return starts again at the mailbox', 'bad']]},
      {id: 'R04', title: 'Pass, policy gap or error? (each asset)', q: 'What did checking this asset find?',
        branches: [['Pass', 'It meets the checks. It goes into the register.', 'good'], ['Policy gap', 'An honest answer that shows the policy is not yet met, such as “no quality plan yet”. It goes into the register and shows up in the measures, so we can offer support. It is not an error.', 'gap'], ['Error', 'A mistake or something unclear. It goes to a person to review and may need a correction.', 'bad']],
        note: 'A policy gap moves forward. Only an error goes sideways for correction.'},
      {id: 'R05', title: 'New entry or update? (adding to the register)', q: 'Is this asset already in the register?',
        branches: [['No, it is a new asset', 'Add it as a new entry', 'good'], ['Yes, and this is a new return or version', 'Update the entry, keeping the record of its source, its checks and our decision', 'good']]}
    ],
    register: ['Organisation', 'Lasting asset reference', 'Submission reference', 'Return version', 'Reporting cycle', 'The 24 details from the version 3 workbook', 'The original file', 'Checking result', 'Review decision', 'Where each value came from'],
    controls: ['Security', 'Audit trail', 'Where data came from (lineage)', 'Version control', 'Records management']
  };

  if (typeof module !== 'undefined' && module.exports) { module.exports = PROCESS; return; }
  root.DAMProcess = PROCESS;
})(this);
