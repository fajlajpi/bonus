# pa_bonus/exports.py
import pandas as pd
from django.http import HttpResponse
from pa_bonus.models import RewardRequest
from django.utils import timezone
import io

def generate_telemarketing_export(reward_request_id):
    """
    Generate an Excel file for telemarketing for a specific reward request
    """
    try:
        reward_request = RewardRequest.objects.get(pk=reward_request_id, status='ACCEPTED')
    except RewardRequest.DoesNotExist:
        return None
    
    # Create a DataFrame for the reward request
    data = []
    items = reward_request.rewardrequestitem_set.select_related('reward')
    
    for item in items:
        data.append({
            'Client Number': reward_request.user.user_number,
            'Client Name': f"{reward_request.user.first_name} {reward_request.user.last_name}",
            'Reward Code': item.reward.abra_code,
            'Reward Name': item.reward.name,
            'Quantity': item.quantity,
            'Point Cost': item.point_cost,
            'Total Point Value': item.quantity * item.point_cost,
            'Request ID': reward_request.id,
            'Request Date': reward_request.requested_at.strftime('%Y-%m-%d'),
            'Notes': reward_request.description
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='RewardRequest', index=False)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['RewardRequest']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 15)  # Client Number
        worksheet.set_column('B:B', 25)  # Client Name
        worksheet.set_column('C:C', 15)  # Reward Code
        worksheet.set_column('D:D', 30)  # Reward Name
        worksheet.set_column('E:E', 10)  # Quantity
        worksheet.set_column('F:F', 12)  # Point Cost
        worksheet.set_column('G:G', 15)  # Total Point Value
        worksheet.set_column('H:H', 10)  # Request ID
        worksheet.set_column('I:I', 12)  # Request Date
        worksheet.set_column('J:J', 40)  # Notes
    
    # Update reward request status to FINISHED
    reward_request.status = 'FINISHED'
    reward_request.save()
    
    # Return the Excel file
    output.seek(0)
    return output.getvalue()