from cgitb import text
import requests
import argparse
import os
import re
import time
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

SLEEP_DURATION = os.getenv("SLEEP_DURATION", 300)

CHECKED_LISTINGS = {}

def row_less_than_or_equal(s1, s2):
    """
    Compare two strings based on custom ordering:
    - Numbers are compared numerically.
    - Letters are compared alphabetically.
    - Mixed alphanumeric strings are compared by treating numbers first, then letters.
    """

    def parse_parts(s):
        # Split the string into parts of numbers and letters
        return re.findall(r'\d+|\D+', s)

    def compare_part(p1, p2):
        if p1.isdigit() and p2.isdigit():
            # Compare numeric parts as integers
            return int(p1) - int(p2)
        elif p1.isdigit():
            # Numeric parts are less than alphabetic parts
            return -1
        elif p2.isdigit():
            # Alphabetic parts are greater than numeric parts
            return 1
        else:
            # Compare alphabetic parts lexicographically
            return (p1 > p2) - (p1 < p2)

    parts1 = parse_parts(s1)
    parts2 = parse_parts(s2)
    
    # Compare parts one by one
    for part1, part2 in zip(parts1, parts2):
        result = compare_part(part1, part2)
        if result != 0:
            return result <= 0

    # If all parts are equal, compare lengths of the parts lists
    return len(parts1) <= len(parts2)

def process_events(event_id, max_price, quantity=2, sections=None, max_row=None):
    results = []
    
    resp = requests.get(f"https://mobile.gametime.co/v2/listings/{event_id}?zListings04=rtm_v0&zListings09=2&zListings13=control&zListings18=show_vaccine_required_listings_true&zListings19=zoom_zoom_v0&zListings20=control&zListings30=jenks&zListings32=control_v1&zListings33=pf_adjustment_enabled&zListings36=flash_zone_harmony_v0&zListings39=valuescore_v1&zListings40=202405_exclusives_v1_2&zListings41=ps_2_rb_1&zListings42=17_piece&zListings43=5_v0&zListings45=zbp_v1&zListings46=super_excl_v1&zListings50=zone_deals_true_v4&sort_order=low_to_high&all_in_pricing=true&quantity={quantity}")
    # raise exception if the status code was not 200
    resp.raise_for_status()
    
    data = resp.json()
    
    listings = data["listings"]
    
    if sections:
        sections = sections.split(",")
    
    for listingid, listing in listings.items():
        # does it fufill price
        if listing['price']['total'] > max_price*100:
            continue
        
        # if weve already sent this listing and the price is not lower
        if listingid in CHECKED_LISTINGS.keys() and CHECKED_LISTINGS[listingid] <= listing['price']['total']:
            continue
        
        # is it in one of the provided sections
        if sections and (listing['spot']['section'] not in sections):
            continue
        
        # is it below max row
        if max_row and (not row_less_than_or_equal(listing['spot']['row'], max_row)):
            continue
                
        results.append({
            "id": listingid,
            "section": listing['spot']['section'],
            "row": listing['spot']['row'],
            "price": listing['price']['total'],
            "section_description": listing['spot']['section_group'],
        })
        
    return results


def format_event_url(event_id):
    resp = requests.get(f"https://mobile.gametime.co/v1/events?id={event_id}")
    # raise exception if the status code was not 200
    resp.raise_for_status()
    
    json_data = resp.json()

    # Access the event data
    event = json_data['events'][0]['event']
    performers = json_data['events'][0]['performers']
    performer_ids = json_data['events'][0]['event']['performers']
    venue = json_data['events'][0]['venue']

    # Extract necessary information
    away_team_id = next(p['id'] for p in performer_ids if p['primary'] == False)
    home_team_id = next(p['id'] for p in performer_ids if p['primary'] == True)
    away_team = next(p['short_name'] for p in performers if p['id'] == away_team_id)
    home_team = next(p['short_name'] for p in performers if p['id'] == home_team_id)
    city = venue['city']
    state = venue['state']
    venue_name = venue['name'].replace(" ","-")
    event_id = event['id']
    event_category = event['category']
    
    # Extract and reformat the date
    date_str = event['datetime_local'].split('T')[0]  # Extract date in YYYY-MM-DD format
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%-m-%-d-%Y")  # Format as M-D-YYYY

    # Format the output string
    result = f"https://gametime.co/{event_category}/{away_team}-at-{home_team}-tickets/{formatted_date}-{city}-{state}-{venue_name}/events/{event_id}".lower()

    return result


def format_response_text(event_id, results):
    
    text_str = "I've found gametime tickets:"
    
    base_url = format_event_url(event_id)
    
    sorted_items = sorted(results, key=lambda x: x["price"])
    
    for item in sorted_items:
        listingid = item["id"]
        listing_url = base_url+"/listings/"+listingid+"/?zoom=10"
        price = "${:,.2f}".format(item["price"]/100)
        section = item["section"]
        row = item["row"]
        desc = item["section_description"]
        text_str = text_str + f"\n\n\n{price}, sec {section}, row {row}\n{listing_url}"
        
        # add to accumulator
        CHECKED_LISTINGS[listingid] = item["price"]
    return text_str
  
  
def send_text_message(to_phone_number, message):
    # failsafe to not send extremely long messages, twilio does not support over 1600
    if len(message)>1600:
        print(f"WARN: Long message of length{len(message)}, trimming")
        message = message[:1601]
    # Create a Twilio client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Send the SMS
    message = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone_number
    )
    
    print(f"Message sent to {to_phone_number}. SID: {message.sid}")



def main():
    print("Starting Gametime price monitor")
    # Create the parser
    parser = argparse.ArgumentParser(description="Process event details.")
    
    # Required arguments
    parser.add_argument('event_id', type=str, help='ID of the event')
    parser.add_argument('max_price', type=float, help='Maximum price for the event')
    parser.add_argument('quantity', type=int, help='Maximum price for the event')
    parser.add_argument('send_to', type=int, help='Phone number to send text to, should be formatted like +16789998212')
    
    # Optional arguments
    parser.add_argument('--sections', type=str, help='Sections for the event')
    parser.add_argument('--max-row', type=str, help='Maximum row number for the event')

    # # Parse the arguments
    args = parser.parse_args()
        
    https_error_count = 0
    while True:
        try:
            listings = process_events(args.event_id, args.max_price, args.quantity, args.sections, args.max_row)
            if listings:
                text = format_response_text(args.event_id, listings)
                send_text_message(args.send_to, text)
        except requests.HTTPError as http_err:
            # Handle HTTP errors
            print(f"ERROR: HTTP error occurred: {http_err}")
            https_error_count+=1
            if https_error_count > 10:
                send_text_message(args.send_to, f"Shutting down gametime script, too many http errors ({https_error_count})\nMost recent is {http_err}")
                break
        except TwilioRestException as e:
            print(f"ERROR: A twilio error occurred: {e}")
            break
        except Exception as err:
            # Handle other errors
            print(f"ERROR: An error occurred: {err}")
            break
        
        time.sleep(SLEEP_DURATION)  # Sleep for 300 seconds (5 minutes)
    
    
    

if __name__ == "__main__":
    main()
    
