# Google Sheet Setup for 100 Scores

## Current Issue
The Google Apps Script is trying to write 100 scores, but the sheet is only showing 10. This is likely because:

1. The sheet doesn't have enough rows
2. The sheet structure needs to be updated
3. The script needs to be run to initialize the sheet

## Solution Steps

### Step 1: Update the Google Sheet Structure

1. **Open your Google Sheet** (ID: 1wDHRWGpje67CGVdZWNo_cORpVgAwc1Cki-RNElMnLqs)

2. **Add more rows**:
   - Select row 1 (header row)
   - Right-click and choose "Insert 100 rows below"
   - This will give you rows 1-101 (header + 100 data rows)

3. **Set up the headers** (if not already done):
   - Row 1, Column A: "Rank"
   - Row 1, Column B: "Player Name" 
   - Row 1, Column C: "Score"
   - Row 1, Column D: "Level"
   - Row 1, Column E: "Date"

### Step 2: Run the Initialize Function

1. **Open Google Apps Script** (script.google.com)
2. **Open your project** with the updated code
3. **Run the `initializeSheet()` function**:
   - In the function dropdown, select "initializeSheet"
   - Click the "Run" button
   - This will format the headers properly

### Step 3: Test the Setup

1. **Test data reading**:
   - Run the `testDataReading()` function
   - Check the logs to see if it can read the sheet

2. **Test score submission**:
   - Try submitting a score from the game
   - Check if it appears in the sheet

## Alternative: Manual Sheet Setup

If the script functions don't work, you can manually set up the sheet:

1. **Format the header row**:
   - Select row 1 (A1:E1)
   - Make text bold
   - Set background color to blue (#4285f4)
   - Set text color to white

2. **Ensure you have 100+ rows**:
   - The sheet should have at least 101 rows (1 header + 100 data)
   - If not, add more rows

## Troubleshooting

### If scores still don't appear:
1. Check the Google Apps Script logs for errors
2. Verify the sheet ID is correct
3. Make sure the sheet name is "Sheet1" (or update the SHEET_NAME constant)
4. Check that the script has permission to edit the sheet

### If you get permission errors:
1. Make sure the Google Apps Script is deployed as a web app
2. Set execution permissions to "Anyone"
3. Re-deploy the script after making changes

## Expected Result

After setup, your sheet should:
- Show 100 scores maximum
- Have proper headers with formatting
- Display level numbers in column D
- Show dates in column E
- Automatically sort by score (highest first)
