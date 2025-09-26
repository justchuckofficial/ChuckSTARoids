// Chucksteroids Email Notification Script
// This is a separate script that monitors the scoreboard for new scores
// and sends email notifications when they are added.

// Configuration - UPDATE THESE VALUES
const CONFIG = {
  // Your email address to receive notifications
  RECIPIENT_EMAIL: 'polaroid@gmail.com', // REPLACE WITH YOUR EMAIL
  
  // The Google Sheet ID for your scoreboard
  SHEET_ID: '1wDHRWGpje67CGVdZWNo_cORpVgAwc1Cki-RNElMnLqs',
  SHEET_NAME: 'Sheet1',
  
  // Column positions (should match your main script)
  RANK_COLUMN: 1,
  NAME_COLUMN: 2,
  SCORE_COLUMN: 3,
  LEVEL_COLUMN: 4,
  DATE_COLUMN: 5,
  
  // Email settings
  SUBJECT_PREFIX: 'Chucksteroids Score Alert',
  SEND_NOTIFICATIONS: true, // Set to false to disable
  
  // How often to check for new scores (in minutes)
  CHECK_INTERVAL_MINUTES: 5
};

// Properties key for tracking last checked score
const LAST_CHECK_KEY = 'last_score_check';

// Main function to check for new scores and send notifications
function checkForNewScores() {
  try {
    console.log('Checking for new scores...');
    
    // Skip if notifications are disabled
    if (!CONFIG.SEND_NOTIFICATIONS) {
      console.log('Email notifications disabled');
      return;
    }
    
    // Skip if email not configured
    if (!CONFIG.RECIPIENT_EMAIL || CONFIG.RECIPIENT_EMAIL === 'your-email@example.com') {
      console.log('Recipient email not configured');
      return;
    }
    
    // Get the last score we checked
    const properties = PropertiesService.getScriptProperties();
    const lastCheckData = properties.getProperty(LAST_CHECK_KEY);
    
    // Get current scores from the sheet
    const sheet = SpreadsheetApp.openById(CONFIG.SHEET_ID).getSheetByName(CONFIG.SHEET_NAME);
    const data = sheet.getDataRange().getValues();
    
    if (data.length <= 1) {
      console.log('No scores found in sheet');
      return;
    }
    
    // Get the most recent score (first data row after header)
    const latestScore = {
      playerName: data[1][CONFIG.NAME_COLUMN - 1] || '',
      score: parseInt(data[1][CONFIG.SCORE_COLUMN - 1]) || 0,
      level: parseInt(data[1][CONFIG.LEVEL_COLUMN - 1]) || 1,
      date: data[1][CONFIG.DATE_COLUMN - 1] || new Date()
    };
    
    // Check if this is a new score
    if (lastCheckData) {
      const lastCheck = JSON.parse(lastCheckData);
      
      // Compare with the last score we checked
      if (lastCheck.playerName === latestScore.playerName && 
          lastCheck.score === latestScore.score && 
          lastCheck.level === latestScore.level) {
        console.log('No new scores found');
        return;
      }
    }
    
    // This is a new score! Send notification
    console.log('New score detected:', latestScore);
    sendScoreNotification(latestScore);
    
    // Update the last checked score
    properties.setProperty(LAST_CHECK_KEY, JSON.stringify(latestScore));
    
  } catch (error) {
    console.error('Error checking for new scores:', error);
  }
}

// Send email notification for a new score
function sendScoreNotification(scoreData) {
  try {
    const { playerName, score, level, date } = scoreData;
    
    // Calculate rank (this is a simplified version)
    const sheet = SpreadsheetApp.openById(CONFIG.SHEET_ID).getSheetByName(CONFIG.SHEET_NAME);
    const data = sheet.getDataRange().getValues();
    const scores = data.slice(1).map(row => ({
      playerName: row[CONFIG.NAME_COLUMN - 1] || '',
      score: parseInt(row[CONFIG.SCORE_COLUMN - 1]) || 0
    })).filter(s => s.score > 0);
    
    scores.sort((a, b) => b.score - a.score);
    const rank = scores.findIndex(s => s.playerName === playerName && s.score === score) + 1;
    
    const subject = `${CONFIG.SUBJECT_PREFIX}: New High Score!`;
    const body = `
New score submitted to Chucksteroids!

Player: ${playerName}
Score: ${score.toLocaleString()}
Level: ${level}
Rank: #${rank}

Submitted at: ${new Date(date).toLocaleString()}

Check the scoreboard: https://docs.google.com/spreadsheets/d/${CONFIG.SHEET_ID}

---
This is an automated notification from your Chucksteroids scoreboard.
    `.trim();
    
    // Send the email
    GmailApp.sendEmail(
      CONFIG.RECIPIENT_EMAIL,
      subject,
      body
    );
    
    console.log(`Email notification sent for score: ${playerName} - ${score}`);
    
  } catch (error) {
    console.error('Failed to send email notification:', error);
  }
}

// Test function to send a sample notification
function testEmailNotification() {
  const testScore = {
    playerName: 'Test Player',
    score: 50000,
    level: 5,
    date: new Date()
  };
  
  console.log('Sending test email notification...');
  sendScoreNotification(testScore);
  console.log('Test email sent!');
}

// Function to set up a time-based trigger (run this once to enable automatic checking)
function setupEmailTrigger() {
  try {
    // Delete any existing triggers
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'checkForNewScores') {
        ScriptApp.deleteTrigger(trigger);
      }
    });
    
    // Create new trigger to run every 5 minutes
    ScriptApp.newTrigger('checkForNewScores')
      .timeBased()
      .everyMinutes(CONFIG.CHECK_INTERVAL_MINUTES)
      .create();
    
    console.log(`Email trigger set up to check every ${CONFIG.CHECK_INTERVAL_MINUTES} minutes`);
    return 'Email trigger set up successfully!';
    
  } catch (error) {
    console.error('Failed to set up email trigger:', error);
    return 'Error: ' + error.toString();
  }
}

// Function to remove the email trigger
function removeEmailTrigger() {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    let removed = 0;
    
    triggers.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'checkForNewScores') {
        ScriptApp.deleteTrigger(trigger);
        removed++;
      }
    });
    
    console.log(`Removed ${removed} email trigger(s)`);
    return `Removed ${removed} email trigger(s)`;
    
  } catch (error) {
    console.error('Failed to remove email trigger:', error);
    return 'Error: ' + error.toString();
  }
}

// Function to manually check for new scores (for testing)
function manualCheck() {
  console.log('Manual check triggered');
  checkForNewScores();
  return 'Manual check completed';
}


