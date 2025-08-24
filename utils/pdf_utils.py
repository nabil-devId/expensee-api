from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib import colors

from schemas.reports.monthly import MonthlyReport

def generate_monthly_report_pdf(report_data: MonthlyReport) -> BytesIO:
    buffer = BytesIO()
    pagesize = (140 * mm, 216 * mm)
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = f"Monthly Expense Report: {report_data.period.label}"
    story.append(Paragraph(title, styles['h1']))
    story.append(Spacer(1, 0.25 * inch))

    # Summary
    summary = report_data.summary
    # NEW, CORRECTED CODE
    summary_data = [
        ['Total Expenses:', f'Rp {summary.total_expenses:,.0f}'],
        ['Total Transactions:', summary.total_transactions],
        ['Average Transaction:', f'Rp {summary.avg_transaction:,.0f}'],
    ]

    # Handle the largest expense separately for clarity and safety
    if summary.largest_expense and summary.largest_expense.date:
        # Format the date object into a human-readable string
        formatted_date = summary.largest_expense.date.strftime("%B %d, %Y")  # e.g., "October 27, 2023"
        
        largest_expense_str = (
            f'Rp {summary.largest_expense.amount:,.0f} on {formatted_date} '
            f'at {summary.largest_expense.merchant_name}'
        )
        summary_data.append(['Largest Expense:', largest_expense_str])
    else:
        summary_data.append(['Largest Expense:', 'N/A'])
    summary_table = Table(summary_data, colWidths=[1.5 * inch, 4 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.25 * inch))

    # Category Breakdown
    story.append(Paragraph("Category Breakdown", styles['h2']))
    category_data = [['Category', 'Amount', 'Percentage', 'Budget Status']]
    for item in report_data.category_breakdown:
        budget_status = "N/A"
        if item.budget:
            status = item.budget.status.value
            remaining = item.budget.remaining
            budget_status = f"{status} (Rp {remaining:,.0f} {'remaining' if remaining >= 0 else 'over'})"

        category_data.append([
            item.category.name,
            f'Rp {item.amount:,.0f}',
            f'{item.percentage}%',
            budget_status
        ])

    category_table = Table(category_data, colWidths=[1.5 * inch, 1 * inch, 1 * inch, 2 * inch])
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(category_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
