# Gametime Price Monitor

## Overview

This Python script monitors ticket prices for a specified event on Gametime. It fetches ticket listings, filters them based on user-defined criteria, and sends an SMS with the details of the tickets that meet the criteria. The script runs indefinitely, checking for updates every 5 minutes.

## Features

- **Price Monitoring:** Retrieves and filters ticket listings based on maximum price, sections, and row number.
- **SMS Notification:** Sends SMS notifications using Twilio when new tickets are available.
- **Custom String Comparison:** Compares alphanumeric strings considering numeric and alphabetical ordering.

## Requirements

- Python 3.x
- Required Python packages:
  - `requests`
  - `twilio`

You can install the required packages using pip:

```bash
pip3 install requests twilio
```

## Environment Variables

Set the following environment variables for Twilio integration:

- **TWILIO_ACCOUNT_SID** - Your Twilio Account SID.
- **TWILIO_AUTH_TOKEN** - Your Twilio Auth Token.
- **TWILIO_PHONE_NUMBER** - Your Twilio phone number.
- **SLEEP_DURATION** - Duration in seconds between checks (default is 300 seconds).

Example:
```bash
export TWILIO_ACCOUNT_SID='your_twilio_account_sid'
export TWILIO_AUTH_TOKEN='your_twilio_auth_token'
export TWILIO_PHONE_NUMBER='your_twilio_phone_number'
export SLEEP_DURATION='300'
```

## Usage

Run the script using the command line with the following arguments:

```bash
python3 gametime_monitor.py <event_id> <max_price> <quantity> <send_to> [--sections <sections>] [--max-row <max_row>]
```

### Arguments
- **event_id** (required): The ID of the event to monitor.
- **max_price** (required): Maximum price for the tickets to be considered.
- **quantity** (required): Number of tickets to check.
- **send_to** (required): Phone number to send SMS notifications to (format: +16789998212).
- **--sections** (optional): Comma-separated list of sections to filter.
- **--max-row** (optional): Maximum row number to filter.

### Example

To monitor an event with ID **6580b5ea0f9c68d289c6e71a**, with a maximum price of $60, and send notifications to **+16789998212**:
```bash
python3 gametime_monitor.py 6580b5ea0f9c68d289c6e71a 60 2 +16789998212 --sections A,B --max-row 10
```

## Script Behavior

1. **Initialization**: The script initializes and starts the monitoring process.
2. **Event Processing**: Retrieves and processes event data from the Gametime API.
3. **Filtering Listings**: Filters listings based on price, sections, and row number.
4. **Formatting and Sending Notifications**: Formats the response and sends an SMS via Twilio if listings are found.
5. **Error Handling**: Handles HTTP errors, Twilio errors, and other exceptions. If too many HTTP errors occur, it will shut down and notify the user.
6. **Repetition**: Waits for the specified sleep duration (default 5 minutes) and repeats the process.

## Error Handling

- **HTTP Errors**: Handles issues related to network requests.
- **Twilio Errors**: Handles errors related to sending SMS.
- **General Exceptions**: Catches other unexpected errors.

If you encounter issues, check the error messages for troubleshooting.