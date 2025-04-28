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
*Ideally, Managers do not need to use Django Admin for anything*
- Managers can set up Brand Bonuses
- Managers can register clients for the system
- Managers can set up Rewards for clients to claim
- Managers can see, review and confirm / deny applications to bonus program
- Managers can see reward claims and confirm / deny them
- Managers can import turnover data, credit note data


### For Sales Reps
*Sales Reps need to see the status of their own clients, but not anyone else's. They also need to have an easy way of helping their clients with the system.*
- Sales Reps can look at their clients
- Reps can see the clients' turnover in brands as well as their point totals
- Reps can see the clients' open reward requests, without being able to modify
- Reps can create reward requests in the name of their clients.

### For Admins
- Admins can see individual transactions
- Admins can upload exports from accounting (raw invoice data) and check their processing

## MVP Functionality
- [x] Uploading accounting data
    - [x] Invoices (points gained for turnover in brands)
    - [x] Credit Notes (points lost for money returned to client)
- [x] Processing accounting data and creating point transactions
- [x] Users can log in and see their points totals as well as transactions history
- [x] Users can see a list of available rewards
- [x] Users can send a reward request
- [x] Tests
- [x] Basic styling

## MVP V2: Going Public
- [x] SMS Notifications (monthly + one shot login info) via CSV
- [x] Email notifications
- [x] Login with email
- [x] Reward Request confirmation
- [x] Reward Request to Telemarketing bridge file
- [ ] Client EXTRA GOAL logic

## TODO
### Backend
- [x] Basic Models layout
- [x] Upload functionality
- [ ] **Invoice data processing**
    - [x] Invoice data into points transactions
        - [x] Transaction fingerprinting - won't create duplicates of the same transaction
    - [x] Credit Note processing
    - [ ] Reading gift invoices and ticking off relevant reward requests
        1. **Match parameters (Client no. + point value) to identify request**
        2. Include request as a text line (issue with importing)
- [ ] **User Views**
    - [x] Current Point Balance
    - [x] Individual Transactions
    - Reward Claims
        - [x] Reward Catalogue
        - [x] Reward Request
            - [ ] Add note for different delivery address to default
        - [x] Reward Request status and review
        - [ ] Reward Request modification of not-yet-approved
    - [ ] User options
        - [ ] Opt in/out of notifications via email/sms
- [x] **Database**
    - [x] Move to PostgreSQL (outdated)
    - [x] Move to mySQL for production
- [ ] **Tests**
    - [x] Add tests as per CodersLab project specs
    - [ ] Add unit tests to all models and views
    - [ ] Prepare test files for uploads
    - [ ] Prepare tests for notifications (email, sms)
- [ ] **Client notifications**
    - EMAIL
        - [ ] Set up SMTP server and test
        - [ ] Schedule emails to send:
            - [ ] Anytime points are added / deducted
            - [ ] Any change to Reward Request Status
    - SMS
        - Found a practical service SMSbrana.cz, charging 1,05 CZK / SMS with prepaid credit
        - Automated sending via CSV or direct API connection
        - [x] CSV export of messages
        - [ ] Initial login / password information
        - [x] Monthly point update
- [ ] **Manager Views**
    - [ ] Clients list
    - [ ] Client detail & Modification
    - [ ] Client Registrations
    - [x] Reward Requests List
    - [x] Reward Request confirmation / modification
    - [ ] Reward RETURNS functionality
    - [ ] Exports for Sales Reps / Directors
        - [ ] Current points
        - [ ] Monthly claims
        - [ ] Stats by sales rep
- [ ] **Sales Rep Views**
    - [ ] Clients List & Goal Progress
    - [ ] Clients transactions
    - [ ] Clients Rewards Requests
    - [ ] Place a request for client
- [ ] Add custom 404
- [x] Refactor tasks.py into more single-responsibility functions rather than one spaghetti function

### Frontend
- [ ] **Public Area**
    - [ ] Login screen
    - [ ] Bonus Programme explanation
    - [ ] Reward Catalogue Teaser
- [ ] **Client Area**
    - [ ] Registration of new client
    - [x] Dashboard
    - [x] List of Point Transactions
    - [ ] Current Goal & progress
    - [ ] New goal submission
    - [x] Bonus Catalogue
    - [x] Reward Request
    - [x] Reward Request List & Status
    - [ ] Reward Request Modification
- [ ] **Manager Area**
    - [x] Dashboard
    - [ ] Clients
        - [x] List of clients
        - [ ] Goals & progress
        - [ ] New registrations
    - [x] Reward Requests
- [ ] **Sales Rep Area**
    - [ ] Dashboard
    - [ ] Client overview
        - [ ] List of clients
        - [ ] Goals & progress
    - [ ] Reward Requests
        - [ ] List & Status
        - [ ] Place a request for client

## Nice to have
- [ ] Internationalization prepared (but postponed due to Hungary launch being shelved for now)
- [ ] Automation options with Abra
    - [ ] Confirmed reward requests automatically loaded into the system?
    - [ ] Current stock status?
- [ ] Look into splitting the functionality into multiple apps
- [ ] New Client Mode
    - *For new clients we can't set a goal or increase, but we want something. Allow new clients to register with a goal, but without a base, and after 6 months, revisit their turnover and consider that a base.*
- [ ] Connect SMSbrana.cz via API to streamline messaging

## Feedback from Sales Reps
- [ ] Prehled OZ a jejich klientů - stav fakturace, bodů, odměn
- [ ] Klientům rozeslat první SMS s loginem a heslem
- [ ] Vracení dárků - opravit reward request, opravit podle toho i transakci
- [ ] Záruka na elektroniku? Jaká? Pan Mach zjišťuje
    - [ ] Záruka na elektroniku je 1 rok
    - [ ] Napsat při potvrzení žádosti o dárky
- [ ] Poštovné za bonusy?
    - Určitě bez, ale hlídat, kdyby se posílalo hodně malých čerpání
- [ ] Workflow - objednává klient u OZ, u toho objednají dárek, co s tím dál? Manažer potvrdí?
    - Výběr dárku/dárků
        - Vybírá sám klient, nebo klient s OZ
    - Vytvoření žádosti o dárek
    - Potvrzení / úprava žádosti manažerem
    - Zpracování žádosti do faktury (1 Kč) (Telemarketing)
    - Kontrola stavu žádosti
    - Potvrzení a uzavření
- [ ] Přidat poznámky k čerpání, aby to telemarketing mohl zpracovávat příslušně
- [ ] Extra bonus pro nové klienty
    - Začne s cílem, ale bez základu
    - Po 6 měsících uvidíme základ, x2, a můžeme stanovovat cíl
- [ ] Letáček se základní informací
    - [ ] 1000 ks
    - [ ] nejzajímavější dárky
    - [ ] značky EC + AE
    - [ ] Body za fakturaci - 8 Kč/bod, 10 Kč/bod
- [ ] Manažerské zásahy do žádostí musejí upravovat i příslušné transakce