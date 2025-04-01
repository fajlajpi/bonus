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
- Managers can import turnover data


### For Sales Reps
- Sales Reps can look at their clients
- Reps can see their turnover in brands as well as their point totals
- Reps can see their open reward requests, without being able to modify
- Reps can create reward requests in the name of their cliemts.

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
    - [x] Reward Request status and review
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
    - [x] See open reward requests
    - [x] Confirm / modify / reject reward requests with a message
    - [ ] See clients' contract details
    - [ ] Track clients' progress
    - [ ] Get exports to pass on to sales reps
- [ ] Look into splitting the functionality into multiple apps
- [ ] Refactor tasks.py into more single-responsibility functions rather than one spaghetti function


## Nice to have
- [ ] Internationalization prepared (but postponed due to Hungary launch being shelved for now)
- [ ] Proper Template structure
- [ ] Anything resembling Front-end

## Feedback from Sales Reps
- [ ] Prehled OZ a jejich klientů - stav fakturace, bodů, odměn
- [ ] Klientům rozeslat první SMS s loginem a heslem
- [ ] Vracení dárků - opravit reward request, opravit podle toho i transakci
- [ ] Záruka na elektroniku? Jaká? Pan Mach zjišťuje
    - [ ] Záruka na elektroniku je 1 rok
    - [ ] Napsat při potvrzení žádosti o dárky
- [ ] Poštovné za bonusy?
- [ ] WOrkflow - objednává klient u OZ, u toho objednají dárek, co s tím dál? Manažer potvrdí?
- [ ] Přidat poznámky k čerpání, aby to telemarketing mohl zpracovávat příslušně
- [ ] Extra bonus pro nové klienty
    - Začne s cílem, ale bez základu
    - Po 6 měsících uvidíme základ, x2, a můžeme stanovovat cíl
- [ ] Letáček se základní informací
    - [ ] 1000 ks
    - [ ] nejzajímavější dárky
    - [ ] značky EC + AE
    - [ ] Body za fakturaci - 8 Kč/bod, 10 Kč/bod
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]
- [ ]