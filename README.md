# PA Bonus Programme 2025

## One-line summary
Django-based system for tracking and using loyalty points

## Target functionality
### For end-users
- Users can register within the system (rather than externally via Google Forms)
- Users can manage their registration, contracts, bonuses within the system
    - All pending approval from Management
- Users can see their points increase and understand where the points came from
- Users can claim rewards for their points from a bonus catalogue
- Users can receive notifications of points gained (monthly) and spent
    - Via email, SMS, WhatsApp

### For Management
- Managers can set up Brand Bonuses
- Managers can set up Rewards for clients to claim
- Managers can see, review and confirm / deny applications to bonus program
- Managers can see reward claims and confirm / deny them

### For Admins
- Admins can see individual transactions
- Admins can upload exports from accounting (raw invoice data) and check their processing

## MVP Functionality
- [ ] Uploading accounting data
    - [X] Invoices (points gained for turnover in brands)
    - [ ] Invoices (points lost for rewards claimed)
    - [x] Credit Notes (points lost for money returned to client)
- [ ] Processing accounting data and creating point transactions
- [x] Users can log in and see their points totals as well as transactions history
- [x] Users can see a list of available rewards
- [x] Users can send a reward request
- [x] TESTS!
- [x] Basic styling

## TODO
- [x] Basic Models layout
- [x] Upload functionality
- [x] Invoice data processing
    - [x] Transaction fingerprinting - won't create duplicates of the same transaction
- [x] Credit Note processing
- [x] User Views
    - [x] Current Point Balance
    - [x] Individual Transactions
- Reward Claims
    - [x] Reward Catalogue
    - [x] Reward Request
    - [ ] Reward Request status and review
- [x] Move to PostgreSQL
- [x] Add tests as per CodersLab project specs
- [ ] Client notifications
    - [ ] When points are added via email
    - [ ] Look into SMS options
- [x] Basic styling
- [ ] Add a landing page for unregistered / logged out visitors
- [ ] Add registrations for new clients
- [ ] Add options and settings for clients
- [ ] Add custom 404
- [ ] Add Managers functionality to dashboard or a separate management view
    - [ ] See open reward requests
    - [ ] Confirm / modify / reject reward requests with a message
    - [ ] See clients' contract details
    - [ ] Track clients' progress
    - [ ] Get exports to pass on to sales reps
- [ ] Look into splitting the functionality into multiple apps
- [ ] Refactor tasks.py into more single-responsibility functions rather than one spaghetti function


## Nice to have
- [ ] Internationalization prepared (but postponed due to Hungary launch being shelved for now)
- [ ] Proper Template structure
- [ ] Anything resembling Front-end

