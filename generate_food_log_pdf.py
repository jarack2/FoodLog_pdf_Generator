import os
import subprocess
import sys
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Table, TableStyle, PageBreak, Spacer
)

CUSTOM_COLORS = {
    'Meal Type': colors.blue,
    'Calories': colors.lightcyan,
    'Portion': colors.papayawhip,
    'Carbs': colors.peachpuff,
    'Protein': colors.lightgreen,
    'Fat': colors.lightyellow,
    'Sugar': colors.pink,
    'Fiber': colors.lavender
}
NUMERIC_COLS = ['calories', 'protein', 'fat', 'sugar', 'fiber', 'carbs']
MEAL_SORT_ORDER = {"Breakfast": 1, "Lunch": 2, "Dinner": 3, "Snack": 4}
STYLES = getSampleStyleSheet()
input_file = ""


def load_and_preprocess_csv(csv_path):
    df = pd.read_csv(csv_path)
    df['day'] = pd.to_datetime(df['day']).dt.date
    df['name'] = df['name'].fillna('')
    df['brand'] = df['brand'].fillna('')
    df['item'] = df['name'] + df['brand'].apply(lambda b: f" ({b})" if b else '')
    df['meal type'] = df['meal type'].fillna('')
    df['portion'] = df['portion'].fillna('')
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df.sort_values('day', inplace=True)
    return df


def create_macro_summary_table(title, totals_dict):
    data = [
        ['Totals'] + [col.title() for col in NUMERIC_COLS],
        [''] + [f"{totals_dict[col]}{' cal' if col == 'calories' else ' g'}" for col in NUMERIC_COLS]
    ]
    table = Table(data, hAlign='LEFT')
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#212529')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),

        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # 'Totals' label left-aligned
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Numbers right-aligned
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),

        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#DEE2E6')),
    ])

    for idx, col in enumerate(NUMERIC_COLS, start=1):
        color = CUSTOM_COLORS.get(col.title())
        if color:
            style.add('BACKGROUND', (idx, 1), (idx, 1), color)
    table.setStyle(style)
    return [Paragraph(f"<b>{title}</b>", STYLES['Heading2']), Spacer(1, 10), table]


def create_item_table(group):
    headers = ['Item', 'Meal Type', 'Portion'] + [col.title() for col in NUMERIC_COLS]
    data = [headers]

    item_style = STYLES['Normal']
    col_widths = [3.5 * inch, 1.0 * inch, 1.0 * inch] + [0.65 * inch] * len(NUMERIC_COLS)

    for _, row in group.iterrows():
        wrapped_item = Paragraph(row['item'], item_style)
        wrapped_portion = Paragraph(row['portion'], item_style)
        data.append([
            wrapped_item,
            row['meal type'],
            wrapped_portion,
            *[f"{int(round(row[col]))}{' cal' if col == 'calories' else ' g'}" for col in NUMERIC_COLS]
        ])
    table = Table(data, repeatRows=1, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8F9FA')),  # Very light grey header
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#212529')),  # Soft off-black text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        # Alignment
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),  # Item and Meal Type left-aligned
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),

        # Subtle Borders
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6')),  # Crisp outer box
        ('LINEABOVE', (0, 1), (-1, 1), 1, colors.HexColor('#DEE2E6')),  # Line under header
        ('INNERGRID', (0, 1), (-1, -1), 0.25, colors.HexColor('#F1F3F5')),  # Extremely faint inner grid
    ])

    # Apply your custom macro background colors to the data rows
    for idx, col in enumerate(headers[2:], start=2):
        color = CUSTOM_COLORS.get(col)
        if color:
            style.add('BACKGROUND', (idx, 1), (idx, -1), color)

    table.setStyle(style)
    return table


def create_doc_template(output_path):
    doc = BaseDocTemplate(output_path, pagesize=landscape(letter), title="Food Log")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='plain', frames=[frame])])
    return doc


def generate_weekly_totals_table(df, story):
    # combined weekly summary table
    weekly_summaries = []
    headers = ['Week'] + [col.title() for col in NUMERIC_COLS]
    weekly_summaries.append(headers)
    for week_num, group in df.groupby('week_num'):
        dates = df.loc[df['week_num'] == week_num].get('day')
        date_range_length = len(set(dates.tolist()))
        week_sum = group[NUMERIC_COLS].sum().astype(int)
        row = [f"Week {week_num} {' (partial)' if date_range_length != 7 else ''}"] + [
            f"{week_sum[col]}{' cal' if col == 'calories' else ' g'}" for col in NUMERIC_COLS
        ]
        weekly_summaries.append(row)
    table = Table(weekly_summaries, hAlign='LEFT', repeatRows=1, colWidths=[1.5 * inch, 1.0 * inch,1.0 * inch,1.0 * inch, None])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#212529')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # 'Week' label left-aligned
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Macros right-aligned
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),

        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.25, colors.HexColor('#DEE2E6')),  # Stronger header divider
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#E9ECEF')),  # Very soft row dividers
    ])
    for idx, col in enumerate(headers[1:], start=1):
        color = CUSTOM_COLORS.get(col)
        if color:
            style.add('BACKGROUND', (idx, 1), (idx, -1), color)
    table.setStyle(style)
    story.append(Paragraph("<b>Weekly Summaries</b>", STYLES['Heading2']))
    story.append(Spacer(1, 10))
    story.append(table)
    story.append(PageBreak())


def generate_daily_entries(df, story):
    # Daily pages
    for day, group in df.groupby('day'):
        group = group.sort_values("meal type", key=lambda x: x.map(MEAL_SORT_ORDER))

        story.append(Paragraph(f"<b>Date: {day.strftime('%B %d, %Y')}</b>", STYLES['Heading2']))
        story.append(Spacer(1, 12))

        day_totals = group[NUMERIC_COLS].sum().astype(int).to_dict()
        story.extend(create_macro_summary_table("Daily Totals", day_totals))
        story.append(Spacer(1, 20))
        story.append(create_item_table(group))
        story.append(PageBreak())


def build_pdf_story(df):
    story = []
    df['week_num'] = pd.to_datetime(df['day']).apply(lambda d: d.isocalendar().week)
    generate_weekly_totals_table(df, story)
    generate_daily_entries(df, story)
    return story

def is_exe():
    """Check if the script is running as a standalone executable."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Otherwise, the script is running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# replaces column headers with more readable ones (and better for processing)
def replace_columns(input_csv):
    path = resource_path("columns.csv")
    with open(path, 'r') as columnsCsv:
        column_headers = columnsCsv.readline()
    with open(input_csv, "r") as csvfile:
        input_lines = csvfile.readlines()
        csvfile.seek(0) # moves back to start of file
        input_lines[0] = column_headers
    with open(input_csv, "w") as csvfile:
        csvfile.writelines(input_lines)
        csvfile.truncate()


def open_pdf(file_path):
    """Open a PDF file with the system's default viewer."""
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        if sys.platform.startswith('darwin'):  # macOS
            subprocess.run(['open', file_path], check=True)
        elif os.name == 'nt':  # Windows
            os.startfile(file_path)
        elif os.name == 'posix':  # Linux
            subprocess.run(['xdg-open', file_path], check=True)
        else:
            print("Unsupported OS.")
    except Exception as e:
        print(f"Failed to open PDF: {e}")


def generate_readable_pdf(input_csv: str, output_pdf: str):
    replace_columns(input_csv)
    df = load_and_preprocess_csv(input_csv)
    print("got df")
    doc = create_doc_template(output_pdf)
    print("created tempalte")
    story = build_pdf_story(df)
    doc.build(story)
    print("built pdf")


def center_window(window, width, height):
    # Ensure the window dimensions are updated and accurate
    window.update_idletasks()

    # Get screen dimensions
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Get the current display scale factor
    scale_factor = window._get_window_scaling()

    # Calculate x and y coordinates for the top-left corner
    # The calculation ensures the center of the window aligns with the center of the screen
    x = int(((screen_width / 2) - (width / 2)) * scale_factor)
    y = int(((screen_height / 2) - (height / 2)) * scale_factor)  # Adjusted y calculation for true center

    # Set the window's geometry
    window.geometry(f"{width}x{height}+{x}+{y}")


def browse_files(window):
    global input_file

    input_file = filedialog.askopenfilename(
        title="Select a file",  # Optional: Customize the dialog title
        initialdir="/",  # Optional: Set the initial directory
        filetypes=(("Comma Separated Values Source Files", "*.csv"), ("All files", "*.*"))  # Optional: Filter file types
    )

    print(input_file)
    window.destroy()


def select_file():
    global input_file
    window = ctk.CTk()
    window.title("Food Log PDF Generator")
    # hack for center spacing
    invisible_text = ctk.CTkLabel(window, text="")
    invisible_text.pack(pady=10)
    text = ctk.CTkLabel(window, text="Select a file to generate a pdf")
    text.pack(pady=5)
    button = ctk.CTkButton(window, text="Browse Files", command=lambda: browse_files(window))
    button.place(y=-20)
    button.pack(padx=50)
    center_window(window, 350, 200)
    window.mainloop()


if __name__ == '__main__':
    select_file()
    print("input file", input_file)
    if input_file:
        output_pdf_file = input_file.replace('.csv', '.pdf')
        generate_readable_pdf(input_file, output_pdf_file)
        open_pdf(output_pdf_file)
