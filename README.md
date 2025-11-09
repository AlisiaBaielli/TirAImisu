# PillPal

## Overview

PillPal is a lightweight medication-assistant prototype. It uses 3 different agents: 
- The calendar agent continously monitors changes in the user's weekly calendar, providing notifications if an event potentially conflicts with the user's treatment
- The email-interaction agent takes as input a new medication, either scanned from a photo or entered manually, and queries a drug interaction database via an API. It determines whether any of the drugs the user is taking negatively interact with the new medication and notifies the user in that case. The notification asks the user whether they would like to email their doctor about this interaction. If the user clicks "yes", the agent automatically generates and sends an email to their doctor.
- The purchasing agent monitors the quantity of each medication that the user has. Once it reaches a threshold (one week's worth), it notifies the user to refill their prescription, and offers to do it for them. If the user accepts, the purchasing agent will interact with the selected pharmacy website to purchase the medication for the user. 

## Instructions

1. Navigate to https://www.website.com
2. Login with any username - password combination
3. Click the "Add Medication" button
4. Scan your medication box if you have it or enter the details manually


