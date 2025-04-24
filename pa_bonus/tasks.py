import pandas as pd
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
import logging
from datetime import datetime
from decimal import Decimal


from .models import (
    FileUpload, PointsTransaction, User, Brand, 
    UserContract, BrandBonus, Invoice, InvoiceBrandTurnover,
    EmailNotification,
)

# Configure logging
logger = logging.getLogger(__name__)

# FILETYPE CONSTANTS TO BRANCH THE PROCESSING
FT_INVOICE = 'INVOICE'
FT_CREDIT_NOTE = 'CREDIT_NOTE'

def process_uploaded_file(upload_id):
    """Main function to process an uploaded file and create invoice records."""
    upload = FileUpload.objects.get(id=upload_id)
    logger.info(f"Starting to process upload {upload_id}")
    
    try:
        mark_upload_as_processing(upload)
        df = read_file(upload.file.path)
        filetype = validate_columns(df)
        
        # Convert and validate dates
        df = process_dates(df)
        
        # First pass: create Invoice and InvoiceBrandTurnover records
        successful_rows = process_invoice_data(df, upload, filetype)
        
        # Second pass: calculate and create points transactions
        points_created = process_points_from_invoices(upload, filetype)
        
        complete_upload(upload, successful_rows)
        logger.info(f"Processing completed. Successful rows: {successful_rows}, Points transactions: {points_created}")
        
    except Exception as e:
        handle_processing_error(upload, e)
        raise


def mark_upload_as_processing(upload):
    """Mark the upload as being processed."""
    upload.status = 'PROCESSING'
    upload.save()


def read_file(file_path):
    """Read the uploaded file and return a dataframe."""
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    logger.info(f"File read successfully. Shape: {df.shape}")
    return df


def validate_columns(df):
    """Validate that the dataframe contains all required columns."""
    required_columns = ['ZČ', 'Cena', 'Kód', 'Datum']
    missing_columns = [col for col in required_columns if col not in df.columns]

    filetype_columns = ['Faktura', 'Dobropis']
    filetype_columns_checked = [col for col in filetype_columns if col in df.columns]

    if len(filetype_columns_checked) != 1:
        raise ValueError(f"Wrong columns for filetype (need either column 'Faktura' or 'Dobropis'), not both or none.")

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    if filetype_columns_checked[0] == 'Faktura':
        return FT_INVOICE
    elif filetype_columns_checked[0] == 'Dobropis':
        return FT_CREDIT_NOTE
    else:
        raise ValueError(f"Unknown type of document, neither invoice or credit note.")


def process_dates(df):
    """Convert date strings in DD.MM.YYYY format to datetime objects."""
    try:
        # Convert 'Datum' from string to datetime
        df['Datum'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y')
        logger.info("Successfully converted dates")
        
        # Check for invalid dates
        invalid_dates = df[df['Datum'].isnull()]
        if not invalid_dates.empty:
            invalid_rows = invalid_dates.index.tolist()
            logger.warning(f"Found {len(invalid_rows)} rows with invalid dates at indices: {invalid_rows}")
            # Filter out rows with invalid dates
            df = df.dropna(subset=['Datum'])
            logger.info(f"Removed {len(invalid_rows)} rows with invalid dates, new shape: {df.shape}")
            
        return df
    except Exception as e:
        logger.error(f"Error processing dates: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to process dates: {str(e)}")


@transaction.atomic
def process_invoice_data(df, upload, filetype):
    """
    First pass processing: Create Invoice and InvoiceBrandTurnover records.
    
    This function processes the raw data and creates Invoice records along with 
    their associated InvoiceBrandTurnover records, irrespective of whether the client
    is registered in the bonus program.
    """
    successful_rows = 0
    errors = []
    
    # Identify the invoice column based on filetype
    invoice_col = 'Faktura' if filetype == FT_INVOICE else 'Dobropis'
    
    # Determine the invoice type
    invoice_type = FT_INVOICE if filetype == FT_INVOICE else FT_CREDIT_NOTE
    
    # Get unique invoices from the file
    unique_invoices = df[invoice_col].unique()
    logger.info(f"Found {len(unique_invoices)} unique invoices in file")
    
    # Create a lookup for all brands in the system to use during processing
    brand_prefixes = {brand.prefix: brand for brand in Brand.objects.all()}
    
    # Process each unique invoice
    for invoice_number in unique_invoices:
        try:
            # Get all rows for this invoice
            invoice_data = df[df[invoice_col] == invoice_number]
            
            if invoice_data.empty:
                continue
                
            # Get the client number and date from the first row
            # (should be the same for all rows in this invoice)
            client_number = invoice_data['ZČ'].iloc[0]
            invoice_date = invoice_data['Datum'].iloc[0]
            if hasattr(invoice_date, 'date'):
                invoice_date = invoice_date.date()
            
            # Calculate total amount for the invoice
            total_amount = Decimal(str(invoice_data['Cena'].sum()))
            
            # Create or update the Invoice record
            invoice, created = Invoice.objects.update_or_create(
                invoice_number=str(invoice_number),
                defaults={
                    'client_number': str(client_number),
                    'invoice_date': invoice_date,
                    'total_amount': total_amount,
                    'invoice_type': invoice_type,
                    'file_upload': upload,
                }
            )
            
            # Process brand turnovers for this invoice
            turnover_created = process_brand_turnovers(invoice, invoice_data, brand_prefixes)
            
            successful_rows += 1
            logger.info(f"Successfully processed invoice {invoice_number}")
            
        except Exception as e:
            error_msg = f"Error processing invoice {invoice_number}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
    
    if errors:
        upload.error_message = "\n".join(errors)
    
    upload.processed_rows = successful_rows
    upload.save()
    
    return successful_rows


def process_brand_turnovers(invoice, invoice_data, brand_prefixes):
    """
    Process and create InvoiceBrandTurnover records for a specific invoice.
    
    This function analyzes the invoice data, identifies brands based on their
    prefix codes, and creates corresponding InvoiceBrandTurnover records.
    """
    turnovers_created = 0
    
    for prefix, brand in brand_prefixes.items():
        # Filter rows for this brand
        brand_rows = invoice_data[invoice_data['Kód'].str.startswith(prefix)]
        
        if brand_rows.empty:
            continue
        
        # Sum up all values for this brand in this invoice
        brand_amount = Decimal(str(brand_rows['Cena'].sum()))
        
        if brand_amount == 0:
            continue
        
        # Create or update the InvoiceBrandTurnover record
        turnover, created = InvoiceBrandTurnover.objects.update_or_create(
            invoice=invoice,
            brand=brand,
            defaults={'amount': brand_amount}
        )
        
        turnovers_created += 1
    
    logger.debug(f"Created {turnovers_created} brand turnover records for invoice {invoice.invoice_number}")
    return turnovers_created


@transaction.atomic
def process_points_from_invoices(upload, filetype):
    """
    Second pass processing: Create points transactions from invoice data.
    
    This function iterates through the Invoice records created in the first pass,
    determines if the client is eligible for points, and creates the appropriate
    PointsTransaction records.
    """
    points_created = 0
    
    # Process only invoices from the current upload
    invoices = Invoice.objects.filter(file_upload=upload)
    logger.info(f"Processing points for {invoices.count()} invoices")
    
    for invoice in invoices:
        try:
            # Check if client exists in our system
            try:
                user = User.objects.get(user_number=invoice.client_number)
            except User.DoesNotExist:
                logger.debug(f"No user found for client number {invoice.client_number} - skipping points")
                continue
            
            # Check if user had an active contract on the invoice date
            contract = get_active_contract(user, invoice.invoice_date)
            if not contract:
                logger.debug(f"No active contract for user {user.user_number} on date {invoice.invoice_date}")
                continue
            
            # Get user's brand bonuses for this contract
            brand_bonuses = contract.brandbonuses.all()
            if not brand_bonuses:
                logger.debug(f"No brand bonuses for user {user.user_number} - skipping")
                continue
            
            # Process each brand turnover for this invoice
            for turnover in invoice.brand_turnovers.all():
                transactions_created = process_brand_points(
                    user, invoice, turnover, brand_bonuses, filetype
                )
                points_created += transactions_created
                
        except Exception as e:
            logger.error(f"Error processing points for invoice {invoice.invoice_number}: {str(e)}", exc_info=True)
    
    return points_created


def get_active_contract(user, date):
    """Retrieve user's active contract for the specific date."""
    try:
        contract = UserContract.objects.get(
            user_id=user,
            is_active=True,
            contract_date_from__lte=date,
            contract_date_to__gte=date
        )
        logger.debug(f"Found active contract for user on date {date}: {contract}")
        return contract
    except UserContract.DoesNotExist:
        logger.info(f"No active contract found for user {user.user_number} on date {date}")
        return None


def process_brand_points(user, invoice, turnover, brand_bonuses, filetype):
    """
    Process points for a specific brand turnover on an invoice.
    
    This function calculates the points based on the brand bonus rules and
    creates the appropriate PointsTransaction record.
    """
    brand = turnover.brand
    amount = turnover.amount
    
    # Find the matching brand bonus
    bonus = None
    for bb in brand_bonuses:
        if bb.brand_id == brand:
            bonus = bb
            break
    
    if not bonus:
        return 0
    
    # Calculate points based on the bonus ratio
    points = int(float(amount) * bonus.points_ratio)
    
    if points == 0:
        return 0
    
    # Determine points sign based on invoice type
    if filetype == FT_CREDIT_NOTE:
        points = -points
        transaction_type = 'CREDIT_NOTE_ADJUST'
        status = 'CONFIRMED'
    else:
        transaction_type = 'STANDARD_POINTS'
        status = 'PENDING'
    
    # Create transaction with robust idempotency check
    existing = check_existing_transaction(user, invoice, brand, transaction_type)
    
    if existing:
        logger.info(f"Skipping duplicate transaction for invoice {invoice.invoice_number}, brand {brand.name}")
        return 0
    
    # Create new transaction
    transaction = PointsTransaction.objects.create(
        user=user,
        value=points,
        date=invoice.invoice_date,
        description=f'{"Invoice" if invoice.invoice_type == FT_INVOICE else "Credit Note"} {invoice.invoice_number}',
        type=transaction_type,
        status=status,
        brand=brand,
        file_upload=invoice.file_upload
    )
    
    logger.debug(f"Created new transaction: {transaction}")
    return 1


def check_existing_transaction(user, invoice, brand, transaction_type):
    """
    Check if a transaction already exists for this invoice and brand.
    
    This provides a robust idempotency check to prevent duplicate transactions.
    """
    invoice_id_str = str(invoice.invoice_number)
    
    # Comprehensive query to catch potential duplicates
    existing = PointsTransaction.objects.filter(
        user=user,
        date=invoice.invoice_date,
        brand=brand,
        type=transaction_type
    ).filter(
        Q(description__contains=invoice_id_str) | 
        Q(description__contains=f"Invoice {invoice_id_str}") | 
        Q(description__contains=f"Credit Note {invoice_id_str}")
    ).first()
    
    return existing


def complete_upload(upload, successful_rows):
    """Mark the upload as completed and update statistics."""
    upload.status = 'COMPLETED'
    upload.processed_at = timezone.now()
    upload.rows_processed = successful_rows
    upload.save()


def handle_processing_error(upload, exception):
    """Handle a fatal error during processing."""
    error_msg = f"Fatal error processing upload: {str(exception)}"
    logger.error(error_msg, exc_info=True)
    upload.status = 'FAILED'
    upload.error_message = error_msg
    upload.processed_at = timezone.now()
    upload.save()


# EMAIL ASYNC TASKS
def send_email_task(notification_id, recipient_email, subject, message):
    """
    Background task to send an email and update the notification record.
    
    This function will be called asynchronously by Django-Q2.
    """
    try:
        # Get the notification object
        notification = EmailNotification.objects.get(id=notification_id)
        
        # Send the email
        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        logger.info(f"Attempting to asynchronously send an email to {recipient_email}")
        
        # Update notification status to indicate success
        notification.status = 'SENT'
        notification.sent_at = timezone.now()
        notification.save()
        
        return True
    except EmailNotification.DoesNotExist:
        # Handle the case where the notification doesn't exist
        return False
    except Exception as e:
        # Update notification status to indicate failure
        try:
            notification = EmailNotification.objects.get(id=notification_id)
            notification.status = 'FAILED'
            notification.save()

            logger.error(f"Error sending email: {str(e)}", exc_info=True)
        except:
            pass
        
        # Re-raise the exception so Django-Q2 can log it
        raise 