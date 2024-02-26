# StarRez and Asana Integration App


## Background: 

The goal behind S2A is to allow event and conference information, which has been previously stored in **StarRez** (a university residential life/housing management platform) to be automatically replicated in **Asana** , a popular task management software that allows for powerful data visualizations, dashboards, and task scheduling. This app and its features were built specifically for Cornell University’s Conference and Event Services Office to make conference and event planning and management more efficient, but can be applied to universities across the country who have similar subscriptions to these two software platforms. 

At its core, S2A is enabled by a built-in feature accessible to StarRez admins called a Data-Subscription. Data-subscriptions can send information about events in packets in JSON format when a specified trigger is detected. These JSON packets will then be parsed locally by S2A, acting as a middleman to format these JSON packets into a proper format that can be parsed by the Asana REST API.  S2A is written in Python using the Flask framework, and sends GET and PUT/POST requests to Asana via HTTP. 

## Setup: 

In order to send any HTTP requests to Asana’s API, you must first register an account with Asana to create an authentication token. More detailed information on the token creation process can be found on Asana’s developer resources website. 
Once you obtain the token, you can also generate a passkey that will be used to ensure only authorized individuals can send HTTP requests to our app. By default, a passkey is required to access the POST route of our flask app, but this can be disabled with comments. 

With both the passkey and API token, you can then store these credentials in a file titled “.env”. S2A already has the required functions to load variables from your .env file. 

The app can be run locally using the Flask development server, or a tunneling tool like ngrok for testing, but for production, it’s currently being hosted in the cloud using PythonAnywhere. 

Once hosted, you can send post requests to the desired url using the /post route, and you should be able to see your updates in StarRez automatically propagate to Asana! 

## Usage: 

There are currently two supported ways in which events are transferred over to Asana. An incoming event can either be a new, unique event not previously seen by Asana, or it can be an already existing event housed in Asana that has new or updated information. S2A determines whether or not a task is new/unique or an existing event using the unique eventID identifier used to identify each StarRez event. The way that the S2A web-app handles these two scenarios is detailed in-depth below: 

### Case 1 – Creating a new Task (new event added to Asana): 

  1. A new event is created in StarRez, either via a customer inquiry, or staff creation.
  2. The new event’s status in StarRez is switched from a Tentative event to Confirmed.
  3. The data-subscription tool is fired, sending a post request to S2A
  4. S2A then formats the information it pulls from StarRez about this event, sending it to Asana.
  5. The new task is created in Asana (will be visible in 2-4 seconds from trigger)! 

### Case 2 – Updating a Task (making updates to an existing event in Asana): 

  1. A new event is created, or an existing event is updated and the trigger is sent from StarRez.
  2. Event information flows from StarRez into Asana.
     a. Same Information
       If the field information flowing into Asana from StarRez matches exactly the field information that is already stored in its 
       corresponding task in Asana, the task in Asana will remain unchanged.
     b. New Information 
       If an event sends new information that is not stored in its corresponding task in Asana, the behavior of the app becomes
       slightly more complicated, but can be broken down into three scenarios.

     Scenario 1*) The field is filled out in Asana, but the information is not filled out in StarRez (ie. Asana is up to date, but           StarRez is not). If the information is known in Asana, but not in StarRez, StarRez will not attempt to overwrite the existing
     Asana data with a blank field. Knowing this, planners are safe to make updates on the Asana interface side, without losing their
     progress to future data-subs. However, they should be cautious if the information they enter differs from what is stored in
     StarRez. This is covered more in Scenario 2.

     Scenario 2) The field is filled out in Asana, and the field is also filled out in StarRez. If the information for the field is the
     same between both Asana and StarRez, nothing will change. However, if the information about a field is mismatched between StarRez
     and Asana, StarRez will persist as the source of truth. In our current design, StarRez will prevail as the source of truth. If
     StarRez says that the date field is 5/12/2024, but Asana (before the data-sub trigger) says that the date is 5/31/2024, the date
     will be overwritten with 5/12/2024. This strategy should hold for all planner updates. If planners want to ensure that the data in
     Asana will remain true and up to date, they should default to ensuring StarRez acts as the source of truth for all event items,
     and only edit Asana when they are confident their changes will not clash with StarRez’s information.

     Scenario 3) The field is filled out in StarRez, but not in Asana. If the information about a field has been filled out in StarRez,
     but the Asana field for that field is blank before the data sub is triggered, That field will be populated with StarRez’s
     information. Again, StarRez acts as the final source of truth. 

*Important note regarding Scenario 1: 
In all three cases, we see that the behavior of S2A was/is intended to ensure that StarRez will act as the source of truth for all conference information. If there is any change that StarRez is not aware of (ie. Scenario 1) where Asana has information that StarRez does not have, it will not attempt to overwrite it, unless it has information that clashes with information that StarRez has. As of now, all multi-enumerated fields, or enumerated fields are untouched by the integration. For example, any item with a dropdown selection shall be untouched by the StarRez integration and will need to be updated purely on the Asana side. 

## Maintenance and Next Steps: 

Occasionally, updates will need to be made to the source code to keep the web app updated on which exact projects to post to. As of now, this will need to be a manual process as CES expectations for conference list formatting will likely change over time, but this is an avenue for automation if the template ever becomes more standardized in the future. 

