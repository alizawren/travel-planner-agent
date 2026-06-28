# Travel Planner Agent

## Description

An agentic AI-powered tool which helps a user plan a trip. The agent returns a complete itinerary with actual flight, hotel, and tourist attractions.

## Instructions

1. Run to install all dependencies:

```
./install_dependencies.sh
```

2. Set environment variables by copying `.env.example` to a file `.env` and adding API keys.

3. Optional: modify `user_info/user_prefs.json` to set home location. Add a .ics calendar file to the `user_info` directory so the agent can select trip dates based off of a schedule.

4. Then run the agent:

```
python agent.py
```

## Example

An example of a returned itinerary:

```
Your Trip Summary:

Home Airport: SJC (San Jose Mineta International Airport)
Destination Airport: JFK (John F. Kennedy International Airport)

Trip Dates: June 28, 2026 – July 7, 2026
Total Trip Length: 10 days

Flight Info:
Flight Number: AA 2576 → AA 1587 (connecting via Phoenix)
Airline: American Airlines
Departure: SJC at 7:24 PM, June 28, 2026
  → Layover: Phoenix Sky Harbor (PHX), 33 min
  → Arrives JFK at 5:44 AM, June 29, 2026
Return: JFK at 7:07 AM, July 7, 2026 → back to SJC
Type: Round Trip (Economy)

Hotel Info:
Hotel Name: Maritime Hotel
Hotel Address: 363 West 16th Street, New York, NY 10011 (Chelsea, Manhattan)
Hotel Phone: N/A
Hotel Website: https://www.themaritimehotel.com/
Room Description: Boutique hotel in the heart of Chelsea, Manhattan, known for its
  iconic porthole windows and nautical-inspired design. Stylish rooms with modern
  amenities in a prime location near the High Line and Meatpacking District.

Itinerary:

Day 1 – June 29 (Arrival Day):
- Arrive at JFK, check into the Maritime Hotel
- Stroll through 14th Street Park to shake off jet lag

Day 2 – June 30:
- The High Line – Walk the iconic 1.45-mile elevated park with city views
  (Open Mon–Sun 7:00 AM–7:00 PM | Free admission)
- Museum of Illusions – Fun, interactive museum just steps from the hotel
  (77 8th Avenue | https://newyork.museumofillusions.us)

Day 3 – July 1:
- The Joyce Theater – World-class contemporary dance performances
  (175 8th Avenue | https://www.joyce.org | +1 212-242-0800)
- Lisson Gallery – Explore cutting-edge contemporary art in Chelsea
  (138 10th Avenue | https://www.lissongallery.com)

Day 4 – July 2:
- Atlantic Theater – Catch a show at this acclaimed off-Broadway theater
  (West 20th Street | https://atlantictheater.org)
- Secret Garden Park – A peaceful hidden gem in Chelsea for an afternoon stroll

Day 5 – July 3:
- Ground Zero Museum Workshop – A moving and educational 9/11 history museum
  (West 14th Street | https://groundzeromuseumworkshop.org | Wed–Sun 11:00 AM–3:00 PM)
- Ulrik Gallery – Contemporary art gallery in Chelsea
  (453 West 17th Street | https://ulrik.nyc | Wed–Sat 12:00–6:00 PM)

Day 6 – July 4 (Independence Day!):
- Atlantic Stage 2 – Enjoy a performance at this intimate theater
  (330 West 16th Street | https://atlantictheater.org)
- 14th Street Square – Enjoy the July 4th atmosphere and fireworks in the city!

Day 7 – July 5:
- Explore Chelsea's art gallery district along 10th Avenue
- Dr. Gertrude B. Kelly Playground & surrounding Chelsea neighborhood walk

Day 8 – July 6:
- Day trip to Central Park, Times Square, or the Metropolitan Museum of Art
  (explore beyond the neighborhood!)
- Evening: Dinner in the Meatpacking District

Day 9 – July 7 (Departure Day):
- Morning checkout from Maritime Hotel
- Head to JFK for return flight home to SJC

Trip Cost Breakdown:
--------------------------------
Flight Cost:     $561.00 (round trip, Economy, American Airlines)
Hotel Cost:      ~$2,700.00 (est. ~$300/night × 9 nights at Maritime Hotel)
Attraction Costs: ~$100.00 (Museum of Illusions ~$30, theater tickets ~$50–70, galleries free)
--------------------------------
Total Trip Cost: ~$3,361.00 (estimated)

```