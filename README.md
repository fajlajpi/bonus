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
- Uploading accounting data
    - Invoices (points gained for turnover in brands)
    - Invoices (points lost for rewards claimed)
    - Credit Notes (points lost for money returned to client)
- Processing accounting data and creating point transactions
- Users can log in and see their points totals as well as transactions history
- Users can see a list of available rewards
- Users can send a reward request
- Basic styling

## TODO
- [DONE] Basic Models layout
- [DONE] Upload functionality
- [DONE] Invoice data processing
- Credit Note processing
- User Views
    - Current Point Balance
    - Individual Transactions
- Reward Claims
    - Reward Catalogue
    - Reward Request
    - Reward Request status and review
- Client notifications
    - When points are added via email
    - Look into SMS options
- Basic styling