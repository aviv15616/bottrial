from multiprocessing import connection

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
import logging
import sqlite3
import shutil
import schedule
import time
from datetime import datetime
import os

def set_reason_for_account(account_id: str,account_type:str, new_reason: str) -> None:
    """Updates the reason for a specific account in the database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE accounts
            SET reason = ?
            WHERE account_id = ? AND account_type = ?
            ''', (new_reason, account_id,account_type))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
def reset_daily_credentials():
    print("Resetting daily credentials for all accounts...")
    accounts = get_accounts_from_db();
    # Your logic to update the database
    for account in accounts:
        account_type = account[0]
        account_id = account[1]
        update_credential(account_type, account_id, 'daily', 0);


def reset_monthly_credentials():
    print("Resetting monthly credentials for all accounts...")
    accounts = get_accounts_from_db();
    # Your logic to update the database
    for account in accounts:
        account_type = account[0]
        account_id = account[1]
        update_credential(account_type, account_id, 'monthly', 0);


def reset_monthly():
    today = datetime.now()
    if today.day == 1:  # Run this function only on the 1st of the month
        reset_monthly_credentials()


schedule.every().day.at("00:00").do(reset_daily_credentials)
schedule.every().day.at("00:01").do(reset_monthly)


def update_credential(account_type, account_id, credential_type, new_value):
    connection = sqlite3.connect('accounts.db')  # Replace with your database connection
    cursor = connection.cursor()

    if credential_type == 'daily':
        cursor.execute("UPDATE accounts SET daily = ? WHERE account_type = ? AND account_id = ?",
                       (new_value, account_type, account_id))
    elif credential_type == 'monthly':
        cursor.execute("UPDATE accounts SET monthly = ? WHERE account_type = ? AND account_id = ?",
                       (new_value, account_type, account_id))

    connection.commit()
    connection.close()


# Replace 'YOUR_TOKEN' with your actual bot token
TOKEN = '7284445294:AAE6JD48RSVRFWVTRaQ_79FeIHui93SiGbA'
ADMIN_ID = 1043448100
SECOND_ADMIN_ID = 7112258311

# Database file path
DB_FILE = 'accounts.db'
BACKUP_FILE = 'accounts_backup.db'

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def increment_daily_monthly(account_type: str, account_id: str) -> None:
    """Increments the daily and monthly fields of a specific account by 1."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Increment daily and monthly fields by 1
        cursor.execute('''
        UPDATE accounts
        SET daily = daily + 1, monthly = monthly + 1
        WHERE account_type = ? AND account_id = ?
        ''', (account_type, account_id))

        conn.commit()

# Initialize database
def initialize_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT NOT NULL,
            account_id TEXT NOT NULL,
            balance REAL,
            branch_number TEXT,
            bank_number TEXT,
            daily REAL,
            monthly REAL,
            reason TEXT NOT NULL,
            UNIQUE(account_type, account_id)
        )
        ''')
        conn.commit()


def add_account_to_db(account_type, account_id, balance, branch_number, bank_number, daily, monthly):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO accounts (account_type, account_id, balance, branch_number, bank_number, daily, monthly)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (account_type, account_id, balance, branch_number, bank_number, daily, monthly))
        conn.commit()


def delete_account_from_db(account_type, account_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM accounts WHERE account_type = ? AND account_id = ?', (account_type, account_id))
        conn.commit()


def get_accounts_from_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT account_type, account_id, balance, branch_number, bank_number, daily, monthly FROM accounts')
        return cursor.fetchall()


def build_account_buttons(action):
    accounts = get_accounts_from_db()
    keyboard = [
        [InlineKeyboardButton(
            f"סוג: {acc[0]} | מזהה: {acc[1]} |יתרה: {acc[2]:.2f}",
            callback_data=f"{action}_{acc[0]}_{acc[1]}")
        ]
        for acc in accounts
    ]
    if action == 'remove':
        keyboard.append(
            [InlineKeyboardButton("חזור לתפריט הראשי", callback_data='return_to_main_menu')]
        )
    return InlineKeyboardMarkup(keyboard)


# Initialize bot logic
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Determine the chat ID to use for sending messages
    if update.message:
        chat_id = update.message.chat_id
    elif update.callback_query:
        chat_id = update.callback_query.message.chat_id
    else:
        # Log or handle the error as needed
        return

    # Create the keyboard based on the user ID
    if user_id in [ADMIN_ID, SECOND_ADMIN_ID]:
        keyboard = [
            [InlineKeyboardButton("הוסף/ ערוך חשבון", callback_data='add_account')],
            [InlineKeyboardButton("מחק חשבון", callback_data='delete_account')],
            [InlineKeyboardButton("רשימת חשבונות", callback_data='view_accounts')],
            [InlineKeyboardButton("העברה", callback_data='transfer')],
            [InlineKeyboardButton("צפה בפעולות", callback_data='view_logs')],
            [InlineKeyboardButton("מחק פעולות", callback_data='delete_logs')],
        ]
        text = 'ברוך הבא! 🌟\n\nבחר אופציה מהתפריט:'
    else:
        keyboard = [
            [InlineKeyboardButton("העברה", callback_data='transfer')]
        ]
        text = 'אה יא תותח 👋\n\nבחר אופציה מהתפריט:'

    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )


def can_receive_amount(account, amount_to_receive, type):
    """
    Checks if the given account can receive the specified amount.

    Parameters:
        account (tuple): A tuple representing the account with the following fields:
                         (account_type, account_id, balance, branch_number, bank_number, daily, monthly)
        amount_to_receive (float): The amount to be received.

    Returns:
        bool: True if the account can receive the amount, False otherwise.
    """
    # Unpack account details
    account_type, account_id, balance, branch_number, bank_number, daily, monthly = account

    # Check if the amount to receive is greater than the current balance
    if amount_to_receive > balance:
        return False
    if account_type != type:
        return False
    # Check if the account is of type M
    if account_type == 'M':
        # Check daily and monthly constraints
        if daily == 2:
            return False
        if monthly == 10:
            return False


    # If all checks pass, return True
    return True


def fetch_logs():
    # Example for fetching logs from a file
    try:
        with open('logs.txt', 'r') as file:
            logs = file.read()
    except Exception as e:
        logs = f"Error fetching logs: {str(e)}"
    return logs


def log_action(action):
    with open('logs.txt', 'a') as file:
        file.write(f"{action}\n")


def delete_logs():
    try:
        with open('logs.txt', 'w') as file:
            file.truncate(0)
        logger.info("Logs deleted successfully.")
    except Exception as e:
        logger.error(f"Error deleting logs: {str(e)}")


def get_account_balance(account_type, account_id):
    # Connect to your database and fetch the account balance
    # Assuming you have a function fetch_balance that queries the balance from your DB
    balance = fetch_balance(account_type, account_id)
    return balance


def fetch_balance(account_type, account_id):
    # Connect to your database (replace with your connection details)
    conn = sqlite3.connect('accounts.db')
    cursor = conn.cursor()

    # Define the query to fetch the balance
    query = '''
    SELECT balance 
    FROM accounts 
    WHERE account_type = ? AND account_id = ?
    '''

    # Execute the query with parameters
    cursor.execute(query, (account_type, account_id))

    # Fetch the result
    result = cursor.fetchone()

    # Close the connection
    conn.close()

    # Return the balance if found, else return 0 or appropriate value
    if result:
        return result[0]
    return 0


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    user_id = query.from_user.id
    data = query.data
    logger.info(f"Callback data received: {data}")

    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await query.message.reply_text('🚫 אין גישה.')
        return

    try:
        if data.startswith('remove_'):
            _, account_type, account_id = data.split('_')
            balance = get_account_balance(account_type, account_id)
            delete_account_from_db(account_type, account_id)
            await query.message.reply_text(f'✅ חשבון {account_id} מסוג {account_type} הוסר.')
            await query.message.reply_text('הרשימה המעודכנת:', reply_markup=build_account_buttons('remove'))
            log_action(f' {user_id} מחק את חשבון {account_type} עם יתרה של: {balance} ב: {datetime.now()}')

        elif data == 'add_account':
            await query.message.reply_text('B(Bit) / P(Pay) / M(Bank):')
            context.user_data['step'] = 'account_type'
        elif data == 'delete_logs':
            # Prompt for confirmation
            keyboard = [
                [InlineKeyboardButton("אשר מחיקת דוח פעולות שוטף", callback_data='confirm_delete_logs')],
                [InlineKeyboardButton("ביטול", callback_data='return_to_main_menu')]
            ]
            await query.message.reply_text('האם אתה בטוח שברצונך למחוק את כל הפעולות?',
                                           reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == 'confirm_delete_logs':
            delete_logs()
            await query.message.reply_text('🗑️ היומנים נמחקו בהצלחה.')

        elif data == 'edit_account':
            # Handle editing account logic here
            pass

        elif data == 'delete_account':
            await query.message.reply_text('בחר חשבון למחיקה:', reply_markup=build_account_buttons('remove'))

        elif data == 'view_accounts':
            await view_accounts(update, context)
        elif data == 'view_logs':
            # Fetch logs
            logs = fetch_logs()
            if not logs:
                await context.bot.send_message(chat_id=query.message.chat_id, text="No logs available.")
            await context.bot.send_message(chat_id=query.message.chat_id, text=logs)
        elif data == 'transfer':
            context.user_data['step'] = 'amount'
            await query.message.reply_text('הכנס כמות להעברה בין 0 ל10000:')
        elif data == 'return_to_main_menu':
            await start(update, context)

    except Exception as e:
        logger.error(f"Error handling button press: {str(e)}")


async def finalize_transfer(update: Update, context: CallbackContext) -> None:
    amount = context.user_data.get('amount')
    account_type = context.user_data.get('account_type_transfer')
    branch_number = context.user_data.get('branch_number')
    bank_number = context.user_data.get('bank_number')
    account_id = context.user_data.get('account_id')
    user_id = update.effective_user.id

    # Get accounts from the database
    accounts = get_accounts_from_db()

    for account in accounts:
        if can_receive_amount(account, amount, account_type):
            # Update the account's balance
            new_balance = account[2] - amount  # Increase balance for the receiving account
            update_balance_in_db(account[0], account[1], new_balance)

            # Log the transfer
            log_action(
                f"{user_id} העביר {amount} לחשבון {account[1]} עם יתרה חדשה של {new_balance} ב: {datetime.now()}"
            )

            # Notify the user
            if account_type == 'M':

                update_account_counts(account_type,account_id)
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר חשבון בנק: {account[1]}\n"
                           f"מספר סניף: {account[3]}\n"
                           f"מספר בנק: {account[4]}\n"
                           f"יתרה חדשה: {new_balance:.2f}")
            else:
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר טלפון: {account[1]}\n"
                           f"יתרה חדשה: {new_balance:.2f}")

            await update.message.reply_text(message, parse_mode='Markdown')
            context.user_data.clear()
            return
    await update.message.reply_text('⚠️ לא נמצא חשבון מתאים להעברה.')
    context.user_data.clear()

async def transfer(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.message.reply_text('🚫 אין גישה.')
        return

    if 'amount' not in context.user_data:
        await update.message.reply_text('הכנס כמות להעברה:')
        context.user_data['step'] = 'amount'
        return

    try:
        amount = float(context.user_data['amount'])
        if not (0 <= amount <= 10000):
            raise ValueError
    except ValueError:
        await update.message.reply_text('🔢 Please enter a valid number between 0 and 10000.')
        return

    if 'account_type' not in context.user_data:
        account_type_keyboard = [
            [InlineKeyboardButton("B", callback_data='B')],
            [InlineKeyboardButton("P", callback_data='P')],
            [InlineKeyboardButton("M", callback_data='M')]
        ]
        reply_markup = InlineKeyboardMarkup(account_type_keyboard)
        await update.message.reply_text('בחר את סוג החשבון:', reply_markup=reply_markup)
        context.user_data['step'] = 'account_type'
        return

    # Fetch and shuffle accounts
    accounts = get_accounts_from_db()
    random.shuffle(accounts)

    # Try to find a suitable account to transfer to
    for account in accounts:
        account_type, account_id, balance, branch_number, bank_number, daily, monthly = account
        if can_receive_amount(account, amount, context.user_data['account_type']):
            new_balance = balance + amount  # Increase balance for the receiving account
            update_balance_in_db(account_type, account_id, new_balance)

            # Update daily and monthly counts if the account is Type M
            if account_type == 'M':
                update_account_counts(account_type, account_id)

            # Log the transfer
            log_action(
                f"{user_id} העביר {amount} לחשבון {account_id} עם יתרה חדשה של {new_balance:.2f} ב: {datetime.now()}"
            )

            # Notify the user
            if account_type == 'M':
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר חשבון בנק: {account_id}\n"
                           f"מספר סניף: {branch_number}\n"
                           f"מספר בנק: {bank_number}\n"
                           f"יתרה חדשה: {new_balance:.2f}")
            else:
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר טלפון: {account_id}\n"
                           f"יתרה חדשה: {new_balance:.2f}")

            await update.message.reply_text(message, parse_mode='Markdown')
            context.user_data.clear()
            return

    await update.message.reply_text('⚠️ לא נמצא חשבון מתאים להעברה.')
    context.user_data.clear()

def update_balance_in_db(account_type, account_id, new_balance):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE accounts SET balance = ? WHERE account_type = ? AND account_id = ?',
            (new_balance, account_type, account_id)
        )
        conn.commit()
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.message.reply_text('🚫 אין גישה.')
        return

    step = context.user_data.get('step')
    message_text = update.message.text
    logger.info(f"Handling step: {step}, Message text: {message_text}")

    if step == 'amount':
        try:
            amount = float(message_text)
            if not (0 <= amount <= 10000):
                raise ValueError
        except ValueError:
            await update.message.reply_text('🔢 Please enter a valid number between 0 and 10000.')
            return

        context.user_data['amount'] = amount
        await update.message.reply_text('בחר סוג חשבון להעברה (B/P/M):')
        context.user_data['step'] = 'account_type_transfer'

    elif step == 'account_type_transfer':
        account_type = message_text.upper()
        if account_type not in ['B', 'P', 'M']:
            await update.message.reply_text('⚠️ Invalid account type. Please enter B, P, or M.')
            return

        context.user_data['account_type_transfer'] = account_type
        await finalize_transfer(update, context)

    elif step == 'account_type':
        account_type = message_text
        if account_type not in ['B', 'P', 'M']:
            await update.message.reply_text('⚠️ Invalid account type. Please enter B, P, or M.')
            return
        context.user_data['account_type'] = account_type
        if account_type in ['B', 'P']:
            await update.message.reply_text('הכנס מספר טלפון:')
            context.user_data['step'] = 'account_id_b_p'
        elif account_type == 'M':
            await update.message.reply_text('הכנס מספר חשבון בנק:')
            context.user_data['step'] = 'account_id_m'

    elif step == 'account_id_b_p':
        context.user_data['account_id'] = message_text
        await update.message.reply_text('הכנס יתרה:')
        context.user_data['step'] = 'balance_b_p'

    elif step == 'balance_b_p':
        try:
            balance = float(message_text)
        except ValueError:
            await update.message.reply_text('🔢 מספרים בלבד.')
            return

        context.user_data['balance'] = balance  # Store the balance in user_data
        account_type = context.user_data.get('account_type')
        branch_number = '0'
        bank_number = '0'
        daily = 0.0
        monthly = 0.0

        if account_type == 'B':
            await update.message.reply_text('הכנס סיבה:')
            context.user_data['step'] = 'customer_id_b'
        else:
            add_account_to_db(account_type, context.user_data['account_id'], balance, branch_number, bank_number, daily,
                              monthly)
            await update.message.reply_text(
                f'✅ חשבון {context.user_data["account_id"]} מסוג {account_type} נוסף/עודכן עם יתרה: {balance}.')
            log_action(
                f"{user_id} הוסיף/עדכן את חשבון {context.user_data['account_id']} עם יתרה של {balance} ב: {datetime.now()}")
            context.user_data.clear()

    elif step == 'customer_id_b':
        context.user_data['customer_id'] = message_text
        balance = context.user_data.get('balance', 'לא מוגדרת')  # Provide default if balance is not set
        account_type = context.user_data.get('account_type')
        branch_number = '0'
        bank_number = '0'
        daily = 0.0
        monthly = 0.0
        add_account_to_db(account_type, context.user_data['account_id'], balance, branch_number, bank_number, daily,
                          monthly)
        await update.message.reply_text(
            f'✅ חשבון {context.user_data["account_id"]} מסוג {account_type} נוסף/עודכן עם יתרה: {balance}.')
        log_action(
            f"{user_id} הוסיף/עדכן את חשבון {context.user_data['account_id']} עם יתרה של {balance} ב: {datetime.now()}")
        context.user_data.clear()

    elif step == 'account_id_m':
        context.user_data['account_id'] = message_text
        await update.message.reply_text('הכנס יתרה:')
        context.user_data['step'] = 'balance_m'

    elif step == 'balance_m':
        try:
            balance = float(message_text)
        except ValueError:
            await update.message.reply_text('🔢 מספרים בלבד.')
            return

        context.user_data['balance'] = balance  # Store the balance in user_data
        await update.message.reply_text('מספר סניף:')
        context.user_data['step'] = 'branch_number_m'

    elif step == 'branch_number_m':
        context.user_data['branch_number'] = message_text
        await update.message.reply_text('מספר בנק:')
        context.user_data['step'] = 'bank_number_m'

    elif step == 'bank_number_m':
        context.user_data['bank_number'] = message_text
        await update.message.reply_text('כמה העברות יומיות:')
        context.user_data['step'] = 'daily_m'

    elif step == 'daily_m':
        try:
            daily = float(message_text)
            if not (0 <= daily <= 2):
                await update.message.reply_text('🔢 Daily amount must be between 0 and 2.')
                return
        except ValueError:
            await update.message.reply_text('🔢 Daily amount must be a number.')
            return
        context.user_data['daily'] = daily
        await update.message.reply_text('כמה העברות חודשיות:')
        context.user_data['step'] = 'monthly_m'

    elif step == 'monthly_m':
        try:
            monthly = float(message_text)
            if not (0 <= monthly <= 10):
                await update.message.reply_text('🔢 Monthly amount must be between 0 and 10.')
                return
        except ValueError:
            await update.message.reply_text('🔢 Monthly amount must be a number.')
            return
        balance = context.user_data.get('balance', 'לא מוגדרת')  # Provide default if balance is not set
        account_type = context.user_data.get('account_type')
        add_account_to_db(account_type, context.user_data['account_id'], balance, context.user_data['branch_number'],
                          context.user_data['bank_number'], context.user_data['daily'], monthly)
        await update.message.reply_text(
            f'✅ חשבון {context.user_data["account_id"]} מסוג {account_type} נוסף/עודכן עם יתרה של: {balance}')
        log_action(
            f"{user_id} הוסיף/עדכן את חשבון {context.user_data['account_id']} עם יתרה של {balance} ב: {datetime.now()}")
        context.user_data.clear()


def update_balance_in_db(account_type, account_id, new_balance):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE accounts SET balance = ? WHERE account_type = ? AND account_id = ?',
            (new_balance, account_type, account_id)
        )
        conn.commit()


async def handle_text(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.message.reply_text('🚫 אין גישה.')
        return

    step = context.user_data.get('step')

    if step == 'account_type':
        account_type = update.message.text
        if account_type not in ['B', 'P', 'M']:
            await update.message.reply_text('⚠️ Invalid account type. Please enter B, P, or M.')
            return
        context.user_data['account_type'] = account_type
        if account_type in ['B', 'P']:
            await update.message.reply_text('הכנס מספר טלפון:')
            context.user_data['step'] = 'account_id_b_p'
        elif account_type == 'M':
            await update.message.reply_text('הכנס מספר חשבון בנק:')
            context.user_data['step'] = 'account_id_m'

    elif step == 'account_id_b_p':
        context.user_data['account_id'] = update.message.text
        await update.message.reply_text('הכנס יתרה:')
        context.user_data['step'] = 'balance_b_p'

    elif step == 'balance_b_p':
        balance = update.message.text
        try:
            balance = float(balance)
        except ValueError:
            await update.message.reply_text('🔢 Balance must be a number.')
            return
        account_type = context.user_data.get('account_type')
        # Default values for B and P accounts
        branch_number = '0'
        bank_number = '0'
        daily = 0.0
        monthly = 0.0
        add_account_to_db(account_type, context.user_data['account_id'], balance, branch_number, bank_number, daily,
                          monthly)
        await update.message.reply_text(
            f'✅ Account {context.user_data["account_id"]} of type {account_type} added/updated.')
        context.user_data.clear()

    elif step == 'account_id_m':
        context.user_data['account_id'] = update.message.text
        await update.message.reply_text('הכנס יתרה:')
        context.user_data['step'] = 'balance_m'

    elif step == 'balance_m':
        balance = update.message.text
        try:
            balance = float(balance)
        except ValueError:
            await update.message.reply_text('🔢 Balance must be a number.')
            return
        await update.message.reply_text('מספר סניף:')
        context.user_data['step'] = 'branch_number_m'
    elif step == 'branch_number_m':
        context.user_data['branch_number'] = update.message.text
        await update.message.reply_text('מספר בנק:')
        context.user_data['step'] = 'bank_number_m'
    elif step == 'bank_number_m':
        context.user_data['bank_number'] = update.message.text
        await update.message.reply_text('כמה העברות יומיות?:')
        context.user_data['step'] = 'daily_m'
    elif step == 'daily_m':
        daily = update.message.text
        try:
            daily = float(daily)
            if not (0 <= daily <= 2):
                await update.message.reply_text('🔢 Daily amount must be between 0 and 2.')
                return
        except ValueError:
            await update.message.reply_text('🔢 Daily amount must be a number.')
            return
        context.user_data['daily'] = daily
        await update.message.reply_text('כמה העברות חודשיות?:')
        context.user_data['step'] = 'monthly_m'

    elif step == 'monthly_m':
        monthly = update.message.text
        try:
            monthly = float(monthly)
            if not (0 <= monthly <= 10):
                await update.message.reply_text('🔢 Monthly amount must be between 0 and 10.')
                return
            if monthly < context.user_data['daily']:
                await update.message.reply_text('⚠️ Monthly amount must be greater than or equal to the daily amount.')
                return
        except ValueError:
            await update.message.reply_text('🔢 Monthly amount must be a number.')
            return
        # Add or update the M account
        add_account_to_db(
            context.user_data['account_type'],
            context.user_data['account_id'],
            float(update.message.text),
            context.user_data['branch_number'],
            context.user_data['bank_number'],
            context.user_data['daily'],
            monthly
        )
        await update.message.reply_text(
            f'✅ חשבון {context.user_data["account_id"]} מסוג {context.user_data["account_type"]} נוסף/עודכן עם יתרה של {context.user_data["balance"]}')
        log_action(
            f"משתמש {user_id} הוסיף.עדכן את חשבון  {context.user_data['account_id']} עם יתרה של {context.user_data['balance']}")
        context.user_data.clear()
    elif step == 'delete_account':
        account_id = update.message.text
        account_type = context.user_data.get('account_type')
        balance = context.user_data.get('balance')
        delete_account_from_db(account_type, account_id)
        await update.message.reply_text(f'✅ חשבון {account_id} מסוג {account_type} הוסר.')
        await update.message.reply_text('הרשימה המעודכנת', reply_markup=build_account_buttons('remove'))
        context.user_data.clear()
    else:
        await update.message.reply_text('פקודה לא מוכרת.')
async def view_accounts(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.callback_query.answer(text='🚫 אין גישה.')
        return
    accounts = get_accounts_from_db()
    if not accounts:
        await update.callback_query.message.reply_text('No accounts found.')
        return
    # Sort accounts by account type
    accounts.sort(key=lambda acc: acc[0])
    message = 'Accounts:\n'
    for acc in accounts:
        if len(acc) == 7:  # Ensure there are exactly 7 values
            account_type, account_id, balance, branch_number, bank_number, daily, monthly = acc
            if account_type == 'M':
                message += (f"*סוג:* {account_type}\n"
                            f"*מספר חשבון בנק:* {account_id}\n"
                            f"*יתרה:* {balance:.2f}\n"
                            f"*מס' סניף:* {branch_number}\n"
                            f"*מס' בנק:* {bank_number}\n"
                            f"*העברות יומיות:* {daily:.2f}\n"
                            f"*העברות חודשיות:* {monthly:.2f}\n\n")
            elif account_type in ['B', 'P']:
                message += (f"*סוג:* {account_type}\n"
                            f"*טלפון:* {account_id}\n"
                            f"*יתרה:* {balance:.2f}\n\n")
        else:
            message += f"Error: Unexpected data format for account ID {acc[1]}\n"

    await update.callback_query.message.reply_text(message, parse_mode='Markdown')
async def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.message.reply_text('🚫 אין גישה.')
        return

    await update.message.reply_text('Bot stopped.')
    context.bot_data['stop'] = True
    backup_db()
def backup_db():
    shutil.copy(DB_FILE, BACKUP_FILE)
    logger.info('Database backup created.')
def initialize_test_accounts():
    """Initialize the database with test accounts having default values."""
    accounts = [
        {'account_type': 'B', 'account_id': '00001', 'balance': 0.0, 'branch_number': '000', 'bank_number': '000',
         'daily': 0.0, 'monthly': 0.0},
        {'account_type': 'M', 'account_id': '00002', 'balance': 0.0, 'branch_number': '000', 'bank_number': '000',
         'daily': 0.0, 'monthly': 0.0},
        {'account_type': 'P', 'account_id': '00001', 'balance': 0.0, 'branch_number': '000', 'bank_number': '000',
         'daily': 0.0, 'monthly': 0.0}
    ]
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for account in accounts:
            cursor.execute('''
            INSERT OR IGNORE INTO accounts (account_type, account_id, balance, branch_number, bank_number, daily, monthly)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (account['account_type'], account['account_id'], account['balance'], account['branch_number'],
                  account['bank_number'], account['daily'], account['monthly']))

        conn.commit()
import random
from telegram import Update
from telegram.ext import CallbackContext

async def transfer(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id not in [ADMIN_ID, SECOND_ADMIN_ID]:
        await update.message.reply_text('🚫 אין גישה.')
        return

    if 'amount' not in context.user_data:
        await update.message.reply_text('הכנס כמות להעברה:')
        context.user_data['step'] = 'amount'
        return

    try:
        amount = float(context.user_data['amount'])
        if not (0 <= amount <= 10000):
            raise ValueError
    except ValueError:
        await update.message.reply_text('🔢 Please enter a valid number between 0 and 10000.')
        return

    if 'account_type' not in context.user_data:
        account_type_keyboard = [
            [InlineKeyboardButton("B", callback_data='B')],
            [InlineKeyboardButton("P", callback_data='P')],
            [InlineKeyboardButton("M", callback_data='M')]
        ]
        reply_markup = InlineKeyboardMarkup(account_type_keyboard)
        await update.message.reply_text('בחר את סוג החשבון:', reply_markup=reply_markup)
        context.user_data['step'] = 'account_type'
        return

    # Fetch and shuffle accounts
    accounts = get_accounts_from_db()
    random.shuffle(accounts)

    # Try to find a suitable account to transfer to
    for account in accounts:
        if can_receive_amount(account, amount, context.user_data['account_type']):
            account_type, account_id, balance, branch_number, bank_number, daily, monthly = account
            new_balance = balance + amount  # Increase balance as we're transferring to this account
            update_account_balance(account_type, account_id, new_balance)
            if account_type == 'M':
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר חשבון בנק: {account_id}\n"
                           f"מספר סניף: {branch_number}\n"
                           f"מספר בנק: {bank_number}\n"
                           f"יתרה חדשה: {new_balance:.2f}")
                log_action(
                    f"{user_id} העביר {amount} לחשבון {account_id} עם יתרה חדשה של {new_balance} ב: {datetime.now()}")
            elif account_type in ['B', 'P']:
                message = (f"העברה על סך {amount:.2f} תועדה!\n\n"
                           f"*פרטי חשבון:*\n"
                           f"סוג: {account_type}\n"
                           f"מספר טלפון: {account_id}\n"
                           f"יתרה חדשה: {new_balance:.2f}")
                log_action(
                    f"{user_id} העביר {amount} לחשבון {account_id} עם יתרה חדשה של {new_balance} ב:{datetime.now()}")
            await update.message.reply_text(message, parse_mode='Markdown')
            context.user_data.clear()
            return

    await update.message.reply_text('לא נמצא חשבון להעביר אליו את הכמות הנבחרת.')
def update_account_balance(account_type, account_id, new_balance):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE accounts
        SET balance = ?
        WHERE account_type = ? AND account_id = ?
        ''', (new_balance, account_type, account_id))
        conn.commit()
def update_account_counts(account_type: str, account_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE accounts
        SET daily = daily + 1,
            monthly = monthly + 1
        WHERE account_type = ? AND account_id = ?
        ''', (account_type, account_id))
        conn.commit()

def main() -> None:
    initialize_db()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()
if __name__ == '__main__':
    main()
