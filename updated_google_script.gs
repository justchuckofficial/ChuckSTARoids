// Chucksteroids Scoreboard API - Complete Code.gs
// This file handles all scoreboard operations

// Configuration file for Chucksteroids Scoreboard API
// Replace YOUR_SHEET_ID with your actual Google Sheet ID

// Google Sheet Configuration
const SHEET_ID = '1wDHRWGpje67CGVdZWNo_cORpVgAwc1Cki-RNElMnLqs'; // Get this from your sheet URL
const SHEET_NAME = 'Sheet1'; // Default sheet name
const RANK_COLUMN = 1; // Column A
const NAME_COLUMN = 2; // Column B  
const SCORE_COLUMN = 3; // Column C
const LEVEL_COLUMN = 4; // Column D - Level number
const DATE_COLUMN = 5; // Column E - Date

// API Configuration
const MAX_SCORES = 100; // Maximum number of scores to keep (increased from 10)
const MIN_SCORE = 1000; // Minimum score to submit
const MAX_NAME_LENGTH = 20; // Maximum player name length

// Rate Limiting (in milliseconds)
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const MAX_SUBMISSIONS_PER_WINDOW = 5; // Max submissions per minute per IP

// Error Messages
const ERROR_MESSAGES = {
  INVALID_SCORE: 'Invalid score. Must be a number greater than ' + MIN_SCORE,
  INVALID_NAME: 'Invalid name. Must be 1-' + MAX_NAME_LENGTH + ' characters',
  RATE_LIMITED: 'Too many submissions. Please wait before trying again',
  SHEET_ERROR: 'Unable to access scoreboard. Please try again later',
  DUPLICATE_PLAYER: 'Player name already exists. Please choose a different name'
};

// Success Messages
const SUCCESS_MESSAGES = {
  SCORE_ADDED: 'Score added successfully!',
  SCORES_RETRIEVED: 'Scores retrieved successfully!'
};

// Main GET handler - reads scores
function doGet(e) {
  try {
    // Set CORS headers for web requests
    const response = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    };
    
    // Get the action parameter
    const action = e.parameter.action || 'get_scores';
    const limit = parseInt(e.parameter.limit) || MAX_SCORES;
    
    if (action === 'get_scores') {
      return getTopScores(limit);
    } else {
      return createErrorResponse('Invalid action', 400);
    }
    
  } catch (error) {
    console.error('doGet error:', error);
    return createErrorResponse(ERROR_MESSAGES.SHEET_ERROR, 500);
  }
}

// Main POST handler - submits scores
function doPost(e) {
  try {
    // Set CORS headers
    const response = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    };
    
    // Parse the POST data
    const data = JSON.parse(e.postData.contents);
    const { playerName, score, level, action } = data;
    
    if (action === 'submit_score') {
      return submitScore(playerName, score, level);
    } else {
      return createErrorResponse('Invalid action', 400);
    }
    
  } catch (error) {
    console.error('doPost error:', error);
    return createErrorResponse(ERROR_MESSAGES.SHEET_ERROR, 500);
  }
}

function getTopScores(limit = MAX_SCORES) {
  try {
    console.log('Starting getTopScores with limit:', limit);
    
    // Open the Google Sheet
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    console.log('Sheet opened successfully');
    
    // Get all data from the sheet
    const data = sheet.getDataRange().getValues();
    console.log('Raw data retrieved:', data.length, 'rows');
    console.log('First few rows:', data.slice(0, 3));
    
    // Skip header row and get scores
    const scores = data.slice(1).map((row, index) => {
      console.log(`Processing row ${index + 2}:`, row);
      return {
        rank: index + 1,
        playerName: row[NAME_COLUMN - 1] || 'Unknown',
        score: parseInt(row[SCORE_COLUMN - 1]) || 0,
        level: parseInt(row[LEVEL_COLUMN - 1]) || 1,
        date: row[DATE_COLUMN - 1] || new Date()
      };
    }).filter(score => {
      console.log('Filtering score:', score);
      return score.score > 0;
    });
    
    console.log('Filtered scores:', scores.length);
    
    // Sort by score (descending) and limit to requested amount
    scores.sort((a, b) => b.score - a.score);
    const topScores = scores.slice(0, Math.min(limit, MAX_SCORES));
    
    // Update ranks
    topScores.forEach((score, index) => {
      score.rank = index + 1;
    });
    
    console.log('Final top scores:', topScores.length);
    
    return createSuccessResponse({
      scores: topScores,
      totalScores: scores.length,
      message: SUCCESS_MESSAGES.SCORES_RETRIEVED
    });
    
  } catch (error) {
    console.error('getTopScores error:', error);
    console.error('Error stack:', error.stack);
    return createErrorResponse(ERROR_MESSAGES.SHEET_ERROR, 500);
  }
}

// Submit a new score to the sheet
function submitScore(playerName, score, level = 1) {
  try {
    // Validate input
    const validation = validateInput(playerName, score, level);
    if (!validation.valid) {
      return createErrorResponse(validation.message, 400);
    }
    
    // Check rate limiting
    if (isRateLimited()) {
      return createErrorResponse(ERROR_MESSAGES.RATE_LIMITED, 429);
    }
    
    // Open the Google Sheet
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    
    // Get current data
    const data = sheet.getDataRange().getValues();
    const scores = data.slice(1).map(row => ({
      playerName: row[NAME_COLUMN - 1] || '',
      score: parseInt(row[SCORE_COLUMN - 1]) || 0,
      level: parseInt(row[LEVEL_COLUMN - 1]) || 1,
      date: row[DATE_COLUMN - 1] || new Date()
    }));
    
    // Check for duplicate player name
    if (scores.some(s => s.playerName.toLowerCase() === playerName.toLowerCase())) {
      return createErrorResponse(ERROR_MESSAGES.DUPLICATE_PLAYER, 400);
    }
    
    // Add new score
    const newScore = {
      playerName: playerName.trim(),
      score: parseInt(score),
      level: parseInt(level) || 1,
      date: new Date()
    };
    
    scores.push(newScore);
    
    // Sort by score (descending)
    scores.sort((a, b) => b.score - a.score);
    
    // Keep only top 100
    const topScores = scores.slice(0, MAX_SCORES);
    
    // Clear existing data (except header)
    const lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow - 1, 5).clear(); // Clear 5 columns now
    }
    
    // Write new data
    topScores.forEach((score, index) => {
      const row = index + 2; // Start from row 2 (after header)
      sheet.getRange(row, RANK_COLUMN).setValue(index + 1);
      sheet.getRange(row, NAME_COLUMN).setValue(score.playerName);
      sheet.getRange(row, SCORE_COLUMN).setValue(score.score);
      sheet.getRange(row, LEVEL_COLUMN).setValue(score.level);
      sheet.getRange(row, DATE_COLUMN).setValue(score.date);
    });
    
    // Log the submission
    console.log(`New score submitted: ${playerName} - ${score} (Level ${level})`);
    
    return createSuccessResponse({
      message: SUCCESS_MESSAGES.SCORE_ADDED,
      newRank: topScores.findIndex(s => s.playerName === playerName) + 1,
      totalScores: topScores.length
    });
    
  } catch (error) {
    console.error('submitScore error:', error);
    return createErrorResponse(ERROR_MESSAGES.SHEET_ERROR, 500);
  }
}

// Validate input data
function validateInput(playerName, score, level = 1) {
  // Validate player name
  if (!playerName || typeof playerName !== 'string') {
    return { valid: false, message: ERROR_MESSAGES.INVALID_NAME };
  }
  
  const trimmedName = playerName.trim();
  if (trimmedName.length < 1 || trimmedName.length > MAX_NAME_LENGTH) {
    return { valid: false, message: ERROR_MESSAGES.INVALID_NAME };
  }
  
  // Validate score
  const scoreNum = parseInt(score);
  if (isNaN(scoreNum) || scoreNum < MIN_SCORE) {
    return { valid: false, message: ERROR_MESSAGES.INVALID_SCORE };
  }
  
  // Validate level (optional, defaults to 1)
  const levelNum = parseInt(level);
  if (isNaN(levelNum) || levelNum < 1) {
    return { valid: false, message: 'Invalid level. Must be a number greater than 0' };
  }
  
  return { valid: true };
}

// Simple rate limiting
function isRateLimited() {
  // Simple rate limiting using PropertiesService
  const properties = PropertiesService.getScriptProperties();
  const now = Date.now();
  const key = 'last_submission_' + now.toString().slice(0, -4); // Minute-based key
  
  const lastSubmission = properties.getProperty(key);
  if (lastSubmission) {
    const count = parseInt(lastSubmission);
    if (count >= MAX_SUBMISSIONS_PER_WINDOW) {
      return true;
    }
    properties.setProperty(key, (count + 1).toString());
  } else {
    properties.setProperty(key, '1');
  }
  
  return false;
}

// Create success response
function createSuccessResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify({
      success: true,
      data: data,
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

// Create error response
function createErrorResponse(message, statusCode) {
  return ContentService
    .createTextOutput(JSON.stringify({
      success: false,
      error: message,
      statusCode: statusCode,
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

function testDataReading() {
  try {
    console.log('Testing data reading...');
    
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    const data = sheet.getDataRange().getValues();
    
    console.log('Data rows:', data.length);
    console.log('First row (headers):', data[0]);
    
    if (data.length > 1) {
      console.log('Second row (first data):', data[1]);
    } else {
      console.log('No data rows found - only headers');
    }
    
    return 'Data reading test passed!';
  } catch (error) {
    console.error('Data reading test failed:', error);
    return 'Error: ' + error.toString();
  }
}

// Initialize the sheet with proper headers
function initializeSheet() {
  try {
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    
    // Set headers
    sheet.getRange(1, RANK_COLUMN).setValue('Rank');
    sheet.getRange(1, NAME_COLUMN).setValue('Player Name');
    sheet.getRange(1, SCORE_COLUMN).setValue('Score');
    sheet.getRange(1, LEVEL_COLUMN).setValue('Level');
    sheet.getRange(1, DATE_COLUMN).setValue('Date');
    
    // Format header row
    const headerRange = sheet.getRange(1, 1, 1, 5);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#4285f4');
    headerRange.setFontColor('white');
    
    console.log('Sheet initialized with headers');
    return 'Sheet initialized successfully!';
  } catch (error) {
    console.error('Sheet initialization failed:', error);
    return 'Error: ' + error.toString();
  }
}