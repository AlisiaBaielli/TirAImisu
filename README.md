# PillPal

## Overview

PillPal is a lightweight medication-assistant prototype. It uses 3 different agents: 
- The calendar agent continously monitors changes in the user's weekly calendar, providing notifications if an event potentially conflicts with the user's treatment
- The email-interaction agent takes as input a new medication, either scanned from a photo or entered manually, and queries a drug interaction database via an API. It determines whether any of the drugs the user is taking negatively interact with the new medication and notifies the user in that case. The notification asks the user whether they would like to email their doctor about this interaction. If the user clicks "yes", the agent automatically generates and sends an email to their doctor.
- The purchasing agent monitors the quantity of each medication that the user has. Once it reaches a threshold (one week's worth), it notifies the user to refill their prescription, and offers to do it for them. If the user accepts, the purchasing agent will interact with the selected pharmacy website to purchase the medication for the user. 

## Instructions

1. Navigate to https://www.website.com
2. Login with any username - password combination.
4. Click on "My Data".
5. Enter at minimum Full Name, Email and Doctor Email. The emails need to be valid, you will receive a sample message in Step 12.
6. Click the back arrow.
7. Click the "Add Medication" button.
8. Scan your medication box if you have it or enter the details manually. To showcase the interaction functionality enter a medication that will interact with another (try Ibuprofen).
9. In the bottom left, ask the agent a question (try "Can I drink alcohol?"). Observe the agent's response.
10.  Click the "Add Medication" button again.
11. Repeat step 8, adding a medication that will interact with the previous one (try Lisinopril). This time try entering a low amount (try 3 pills) and enter a high frequency (try Daily) so that it will trigger the purchasing agent.
12. If you followed Step 10 correctly, observe the notification of low medication, click the "Yes" button if you want the agent to buy medication for you. The agent will interact with the pharmacy website in the backend.
13. If you entered two medications that interact negatively in Steps 8 and 11, observe the interaction notification. Click the "Email Your Doctor" button to send an email to Doctor Email.

