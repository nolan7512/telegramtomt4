#!/usr/bin/env python3
import asyncio
import logging
import math
import os
import re

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from metaapi_cloud_sdk import MetaApi
from prettytable import PrettyTable
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, ConversationHandler, CallbackContext

# MetaAPI Credentials
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")

# Telegram Credentials
TOKEN = os.environ.get("TOKEN")
TELEGRAM_USER = os.environ.get("TELEGRAM_USER")
CHANNEL_USER = os.environ.get("CHANNEL_USER")

# Heroku Credentials
APP_URL = os.environ.get("APP_URL")

# Port number for Telegram bot web hook
PORT = int(os.environ.get('PORT', '8443'))


# Enables logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# possibles states for conversation handler
CALCULATE, TRADE, DECISION, ERROR = range(4)

# allowed FX symbols
SYMBOLS = ['AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAGUSD', 'XAUUSD','GOLD']
SYMBOLSPLUS = ['AUD/CAD', 'AUD/CHF', 'AUD/JPY', 'AUD/NZD', 'AUD/USD', 'CAD/CHF', 'CAD/JPY', 'CHF/JPY', 'EUR/AUD', 'EUR/CAD', 'EUR/CHF', 'EUR/GBP', 'EUR/JPY', 'EUR/NZD', 'EUR/USD', 'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'GBP/JPY', 'GBP/NZD', 'GBP/USD', 'NZD/CAD', 'NZD/CHF', 'NZD/JPY', 'NZD/USD', 'USD/CAD', 'USD/CHF', 'USD/JPY', 'XAG/USD', 'XAU/USD','GOLD']
TYPETRADE = ['BUY','BUY LIMIT','BUY NOW','SELL','SELL LIMIT','SELL NOW']
OTHER = ['@','Entry','TP','SL','STOP LOSS','TAKE PROFIT','TARGET PROFIT']

# RISK FACTOR
RISK_FACTOR = float(os.environ.get("RISK_FACTOR"))

# Helper Functions
def CheckSymbolArray(stringcheck,array)-> int:
    """Check string in array if True return 1m if fasle return 0

    Arguments:
        stringcheck : string input for find in array
        array       : array for foreach find string input
    """
    checkstr = 0
    for element in array:
        calcu = stringcheck.upper().find(element,0)
        if(calcu!=-1):
            checkstr = 1
            return checkstr
    return checkstr

def CheckSymbolStr(stringcheck,stringsrc)-> int:
    """Check string in array if True return 1m if fasle return 0

    Arguments:
        stringcheck : string input for find in array
        array       : array for foreach find string input
    """
    checkstr = 0
    calcu = stringsrc.find(stringcheck,0)
    if(calcu!=-1):
        checkstr = 1
        return checkstr
    return checkstr

def FindTP(alphacheck,signalsrc) -> float: 
    arrayfind=[]
    alphacheck = alphacheck.lower()
    for i in range(len(signalsrc)):
        if(signalsrc[i] != ''):
            j = signalsrc[i].lower().find(alphacheck,0)
            if(j!=-1):
                tpfindvar = float((signalsrc[i].split())[-1])
                arrayfind.append(tpfindvar)
    return arrayfind

def remove_pips(signal):
  temp = re.sub(r"(pips|\(.+\))|(pip|\(.+\))|(scalper|\(.+\))|(intraday|\(.+\))|(swing|\(.+\))", "", signal)
  return temp

# def find_entry_point(trade: str, signal: list[str], signaltype : str) -> float:
#     first_line_with_order_type = next((i for i in range(len(signal)) if signal[i].upper().find(order_type_to_find, 0) != -1), -1)

#     try:
#         entry_price = float(re.split('[a-z]+|[-,/,@]', signal[first_line_with_order_type], flags=re.IGNORECASE)[-1])
#     except ValueError:
#         entry_price = None
#     return entry_price   
def replace_spaces(text):
  """
  Thay thế khoảng trắng nằm giữa 2 số thành dấu .

  Args:
    text: Chuỗi cần xử lý

  Returns:
    Chuỗi đã được xử lý
  """
  temp = re.sub(r"(\d+) +(\d+)(?!0)", r"\1.\2", text)
  return temp

def ParseSignal(signal: str) -> dict:
    """Starts process of parsing signal and entering trade on MetaTrader account.

    Arguments:
        signal: trading signal

    Returns:
        a dictionary that contains trade signal information
    """

    # converts message to list of strings for parsing
    signal = remove_pips(signal)
    signal = replace_spaces(signal)
    signal = signal.splitlines()
    signal = [line.rstrip() for line in signal]
    
    #signalstripemty = [x.strip(' ') for x in signal]

    trade = {}

    # determines the order type of the trade
    if('Buy Limit'.lower() in signal[0].lower() or 'Buy Limit'.lower() in signal[1].lower() or'Buy Limit'.lower() in signal[2].lower() ):
        trade['OrderType'] = 'Buy Limit'

    elif('Sell Limit'.lower() in signal[0].lower() or 'Sell Limit'.lower() in signal[1].lower() or 'Sell Limit'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Sell Limit'

    elif('Buy Stop'.lower() in signal[0].lower() or 'Buy Stop'.lower() in signal[1].lower() or 'Buy Stop'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Buy Stop'

    elif('Sell Stop'.lower() in signal[0].lower() or 'Sell Stop'.lower() in signal[1].lower() or 'Sell Stop'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Sell Stop'

    elif('Buy Now'.lower() in signal[0].lower() or 'Buy Now'.lower() in signal[1].lower() or 'Buy Now'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Buy Now'
                
    elif('Sell Now'.lower() in signal[0].lower() or 'Sell Now'.lower() in signal[1].lower() or 'Sell Now'.lower() in signal[2].lower()):
         trade['OrderType'] = 'Sell Now'
         
    elif('Buy'.lower() in signal[0].lower() or 'Buy'.lower() in signal[1].lower() or 'Buy'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Buy'
         
    elif('Sell'.lower() in signal[0].lower() or 'Sell'.lower() in signal[1].lower() or 'Sell'.lower() in signal[2].lower()):
        trade['OrderType'] = 'Sell'
        
    
    
    # returns an empty dictionary if an invalid order type was given
    else:
        return {}
       
    # extracts symbolplus '/' from trade signal if found then replace '/' to ''
    symbolflag = 0
    for elemental in SYMBOLSPLUS:
        calcusymbol = signal[0].upper().find(elemental,0)
        if(calcusymbol != -1):
            trade['Symbol'] = elemental.replace('/','')
            symbolflag = 1
            
    # extracts symbol from trade signal        
    if(symbolflag == 0):                
        for element in SYMBOLS:
            calcu = signal[0].upper().find(element,0)
            if(calcu != -1):
                trade['Symbol'] = element
                
    # checks if the symbol is valid, if not, returns an empty dictionary
    if(trade['Symbol'] not in SYMBOLS):
        return {}
    
    # change symbol trade signal
    if(trade['Symbol'] == 'GOLD'):
       trade['Symbol'] = 'XAUUSD'
    
    #Find symbol 'Entry' if found 'entry' will get float entry in Signal and specical Entry = NOW
    entrygetbuy = FindTP('ENTRY',signal)
    flagbuyentry = 0
    if(len(entrygetbuy)>0):
        trade['Entry'] = float(entrygetbuy[0])
        flagbuyentry = 1
        
   # checks entry for 'BUY'/'SELL' OrderType
    if((trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Sell') and flagbuyentry == 0):                
        memforfindorderentry = trade['OrderType'].upper()
        for i in range(len(signal)):
          if(signal[i] != ''):   
              j = signal[i].upper().find(memforfindorderentry,0)
              if(j != -1 and i == 0 ):
                getentryfirstline = re.split('[a-z]+|[-,/,@]',signal[i] ,flags=re.IGNORECASE)[-1]
                if(getentryfirstline != ''):
                    trade['Entry'] = float(getentryfirstline)
                else:
                    trade['Entry'] = ''    
              elif(j != -1 and i > 0):
                  getentrybyline = re.split('[a-z]+|[-,/,@]',signal[i] ,flags=re.IGNORECASE)[-1]
                  if(getentrybyline != ''):
                      trade['Entry'] = float(getentrybyline)
                  else:
                      trade['Entry'] = ''

        # elif(getentryfirstline == '' and signal[1] != ''):            
        #    trade['Entry'] = float((signal[1].split())[-1]) 
           
        # else:
        #     trade['Entry'] = float((signal[2].split())[-1])


    # checks wheter or not to convert entry to float because of market exectution option ("NOW")
    if((trade['OrderType'] == 'Buy Limit' or trade['OrderType'] == 'Sell Limit') and flagbuyentry == 0):
        oneline = re.split('[a-z]+|[-,/,@]',signal[0] ,flags=re.IGNORECASE)[-1]
        if(oneline != ''):
            trade['Entry'] = float(oneline)
            
        elif(oneline == '' and signal[1] != ''):            
           trade['Entry'] = float((signal[1].split())[-1]) 
           
        else:
            trade['Entry'] = float((signal[2].split())[-1])
             
      
    # checks wheter or not to convert entry to float because of market exectution option ("NOW")
    if(trade['OrderType'] == 'Buy Now' or trade['OrderType'] == 'Sell Now'):
        trade['Entry'] = 'NOW'
    
    #Change symbol ordertype from buy/sell to buy limit/sell limit with if : trade['Entry'] != NOW
    if(trade['OrderType'] == 'Buy' and  trade['Entry'] != 'NOW' and trade['Entry'] != ''):
        trade['OrderType'] = 'Buy Limit'
    elif(trade['OrderType'] == 'Sell' and  trade['Entry'] != 'NOW' and trade['Entry'] != ''):
        trade['OrderType'] = 'Sell Limit'
    elif(trade['OrderType'] == 'Buy' and  trade['Entry'] != 'NOW' and trade['Entry'] == ''):
        trade['Entry'] = 'NOW'
    elif(trade['OrderType'] == 'Sell' and  trade['Entry'] != 'NOW' and trade['Entry'] == ''):
         trade['Entry'] = 'NOW'
    
    
    #find and add TP
    arraytp = FindTP('TP',signal)
    arraytarget = FindTP('Target Profit',signal)
    if(len(arraytp) > 0):
        trade['TP'] = arraytp
    elif(len(arraytarget) > 0 and len(arraytp) == 0):
        trade['TP'] = arraytarget
    else:
        trade['TP']= [float((signal[3].split())[-1])]
    
    #find and add SL
    stoplosser = FindTP('SL',signal)
    stoplosserb = FindTP('STOP LOSS',signal)
    if(len(stoplosser) > 0):
        trade['StopLoss'] = float(stoplosser[0])
    elif(len(stoplosserb) > 0 and len(stoplosser) == 0):
        trade['StopLoss'] = float(stoplosserb[0])
    else:
        trade['StopLoss'] = float((signal[2].split())[-1])
    
    # adds risk factor to trade
    trade['RiskFactor'] = RISK_FACTOR

    return trade


def GetTradeInformation(update: Update, trade: dict, balance: float) -> None:
    """Calculates information from given trade including stop loss and take profit in pips, posiition size, and potential loss/profit.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
    """

    # calculates the stop loss in pips
    if(trade['Symbol'] == 'XAUUSD'):
        multiplier = 0.1

    elif(trade['Symbol'] == 'XAGUSD'):
        multiplier = 0.001

    elif(str(trade['Entry']).index('.') >= 2):
        multiplier = 0.01

    else:
        multiplier = 0.0001

    # calculates the stop loss in pips
    stopLossPips = abs(round((trade['StopLoss'] - trade['Entry']) / multiplier))

    # calculates the position size using stop loss and RISK FACTOR
    trade['PositionSize'] = math.floor(((balance * trade['RiskFactor']) / stopLossPips) / 10 * 100) / 100

    # calculates the take profit(s) in pips
    takeProfitPips = []
    for takeProfit in trade['TP']:
        takeProfitPips.append(abs(round((takeProfit - trade['Entry']) / multiplier)))
    tradeTP =[]
    for takeProfit in trade['TP']:
        tradeTP.append(takeProfit)
        
    # creates table with trade information
    table = CreateTable(trade, balance, stopLossPips, takeProfitPips, tradeTP)
    
    # sends user trade information and calcualted risk
    update.effective_message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)

    return

def CreateTable(trade: dict, balance: float, stopLossPips: int, takeProfitPips: int, tradeTP : float) -> PrettyTable:
    """Creates PrettyTable object to display trade information to user.

    Arguments:
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
        stopLossPips: the difference in pips from stop loss price to entry price

    Returns:
        a Pretty Table object that contains trade information
    """

    # creates prettytable object
    table = PrettyTable()
    
    table.title = "Trade Information"
    table.field_names = ["Key", "Value"]
    table.align["Key"] = "l"  
    table.align["Value"] = "l" 

    table.add_row([trade["OrderType"] , trade["Symbol"]])
    table.add_row(['Entry\n', trade['Entry']])

    table.add_row(['Stop Loss', '{} pips'.format(stopLossPips)])

    for count, takeProfit in enumerate(takeProfitPips):
        table.add_row([f'TP {count + 1}', f'({takeProfit} pips)'])
    table.add_row(['\n', '']) 
    table.add_row(['Stop Loss', trade['StopLoss']])
    for count, tradeTPflt in enumerate(tradeTP):
        table.add_row([f'TP {count + 1}', f'{tradeTPflt}'])

    table.add_row(['\nRisk Factor', '\n{:,.0f} %'.format(trade['RiskFactor'] * 100)])
    table.add_row(['Position Size', trade['PositionSize']])
    
    table.add_row(['\nCurrent Balance', '\n$ {:,.2f}'.format(balance)])
    table.add_row(['Potential Loss', '$ {:,.2f}'.format(round((trade['PositionSize'] * 10) * stopLossPips, 2))])

    # total potential profit from trade
    totalProfit = 0

    for count, takeProfit in enumerate(takeProfitPips):
        profit = round((trade['PositionSize'] * 10 * (1 / len(takeProfitPips))) * takeProfit, 2)
        table.add_row([f'TP {count + 1} Profit', '$ {:,.2f}'.format(profit)])
        
        # sums potential profit from each take profit target
        totalProfit += profit

    table.add_row(['\nTotal Profit', '\n$ {:,.2f}'.format(totalProfit)])

    return table

async def ConnectMetaTrader(update: Update, trade: dict, enterTrade: bool):
    """Attempts connection to MetaAPI and MetaTrader to place trade.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information

    Returns:
        A coroutine that confirms that the connection to MetaAPI/MetaTrader and trade placement were successful
    """

    # creates connection to MetaAPI
    api = MetaApi(API_KEY)
    
    try:
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        initial_state = account.state
        deployed_states = ['DEPLOYING', 'DEPLOYED']

        if initial_state not in deployed_states:
            #  wait until account is deployed and connected to broker
            logger.info('Deploying account')
            await account.deploy()

        logger.info('Waiting for API server to connect to broker ...')
        await account.wait_connected()

        # connect to MetaApi API
        connection = account.get_rpc_connection()
        await connection.connect()

        # wait until terminal state synchronized to the local state
        logger.info('Waiting for SDK to synchronize to terminal state ...')
        await connection.wait_synchronized()

        # obtains account information from MetaTrader server
        account_information = await connection.get_account_information()

        update.effective_message.reply_text("Successfully connected to MetaTrader!\nCalculating trade risk ... 🤔")

        # checks if the order is a market execution to get the current price of symbol
        if(trade['Entry'] == 'NOW'):
            price = await connection.get_symbol_price(symbol=trade['Symbol'])

            # uses bid price if the order type is a buy
            if(trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Buy Now'):
                trade['Entry'] = float(price['bid'])

            # uses ask price if the order type is a sell
            if(trade['OrderType'] == 'Sell' or trade['OrderType'] == 'Sell Now'):
                trade['Entry'] = float(price['ask'])

        # produces a table with trade information
        GetTradeInformation(update, trade, account_information['balance'])
            
        # checks if the user has indicated to enter trade
        if(enterTrade == True):

            # enters trade on to MetaTrader account
            update.effective_message.reply_text("Entering trade on MetaTrader Account ... 👨🏾‍💻")

            try:
                # executes buy market execution order
                if(trade['OrderType'] == 'Buy'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)
                
                # executes buy market execution order
                if(trade['OrderType'] == 'Buy Now'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)

                # executes buy limit order
                elif(trade['OrderType'] == 'Buy Limit'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_limit_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes buy stop order
                elif(trade['OrderType'] == 'Buy Stop'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_stop_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes sell market execution order
                elif(trade['OrderType'] == 'Sell'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)
                
                # executes sell now market execution order
                elif(trade['OrderType'] == 'Sell Now'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)
                
                # executes sell limit order
                elif(trade['OrderType'] == 'Sell Limit'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_limit_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes sell stop order
                elif(trade['OrderType'] == 'Sell Stop'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_stop_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)
                
                # sends success message to user
                update.effective_message.reply_text("Trade entered successfully! 💰")
                
                # prints success message to console
                logger.info('\nTrade entered successfully!')
                logger.info('Result Code: {}\n'.format(result['stringCode']))
            
            except Exception as error:
                logger.info(f"\nTrade failed with error: {error}\n")
                update.effective_message.reply_text(f"There was an issue 😕\n\nError Message:\n{error}")
    
    except Exception as error:
        logger.error(f'Error: {error}')
        update.effective_message.reply_text(f"There was an issue with the connection 😕\n\nError Message:\n{error}")
    
    return


# Handler Functions
def PlaceTrade(update: Update, context: CallbackContext) -> int:
    """Parses trade and places on MetaTrader account.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    # checks if the trade has already been parsed or not
    #if(context.user_data['trade'] is None):

    try: 
        # parses signal from Telegram message
        #errorMessage1 = f"There was \nError: {update.effective_message.text}\n."
        #update.effective_message.reply_text(errorMessage1)
        trade = ParseSignal(update.effective_message.text)
        #update.effective_message.reply_text(trade)
        
        # Test Done OK Here
        
        # checks if there was an issue with parsing the trade
        if(not(trade)):
            raise Exception('Invalid Trade')

        # sets the user context trade equal to the parsed trade
        #Fixing here
        #context.user_data['trade'] = trade
        
        update.effective_message.reply_text("Trade Successfully Parsed! 🥳\nConnecting to MetaTrader ... \n(May take a while) ⏰")
    
    except Exception as error:
        logger.error(f'Error: {error}')
        errorMessage = f"There was an error parsing this trade 😕\n\nError: {error}\n"
        update.effective_message.reply_text(errorMessage)

        # returns to TRADE state to reattempt trade parsing
        return TRADE
    
    # attempts connection to MetaTrader and places trade
    asyncio.run(ConnectMetaTrader(update, trade, True))
    
    # removes trade from user context data
    #context.user_data['trade'] = None

    return TRADE

def CalculateTrade(update: Update, context: CallbackContext) -> int:
    """Parses trade and places on MetaTrader account.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    # checks if the trade has already been parsed or not
    if(context.user_data['trade'] is None ):

        try: 
            # parses signal from Telegram message
            trade = ParseSignal(update.effective_message.text)
            
            # checks if there was an issue with parsing the trade
            if(not(trade)):
                raise Exception('Invalid Trade')

            # sets the user context trade equal to the parsed trade
            context.user_data['trade'] = trade
            update.effective_message.reply_text("Trade Successfully Parsed! 🥳\nConnecting to MetaTrader ... (May take a while) ⏰")
        
        except Exception as error:
            logger.error(f'Error: {error}')
            errorMessage = f"There was an error parsing this trade 😕\n\nError: {error}\n"
            update.effective_message.reply_text(errorMessage)

            # returns to CALCULATE to reattempt trade parsing
            return CALCULATE
    
    # attempts connection to MetaTrader and calculates trade information
    asyncio.run(ConnectMetaTrader(update, context.user_data['trade'], False))

    # asks if user if they would like to enter or decline trade
    update.effective_message.reply_text("Would you like to enter this trade?\nTo enter, select: /yes\nTo decline, select: /no")

    return DECISION

def unknown_command(update: Update, context: CallbackContext) -> None:
    """Checks if the user is authorized to use this bot or shares to use /help command for instructions.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)and not(update.effective_message.chat.username == CHANNEL_USER)):
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return

    update.effective_message.reply_text("Unknown command. Use /trade to place a trade or /calculate to find information for a trade. You can also use the /help command to view instructions for this bot.")

    return


# Command Handlers
def welcome(update: Update, context: CallbackContext) -> None:
    """Sends welcome message to user.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    welcome_message = "Welcome to the FX Signal Copier Telegram Bot! 💻💸\n\nYou can use this bot to enter trades directly from Telegram and get a detailed look at your risk to reward ratio with profit, loss, and calculated lot size. You are able to change specific settings such as allowed symbols, risk factor, and more from your personalized Python script and environment variables.\n\nUse the /help command to view instructions and example trades."
    
    # sends messages to user
    update.effective_message.reply_text(welcome_message)

    return

def help(update: Update, context: CallbackContext) -> None:
    """Sends a help message when the command /help is issued

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    help_message = "This bot is used to automatically enter trades onto your MetaTrader account directly from Telegram. To begin, ensure that you are authorized to use this bot by adjusting your Python script or environment variables.\n\nThis bot supports all trade order types (Market Execution, Limit, and Stop)\n\nAfter an extended period away from the bot, please be sure to re-enter the start command to restart the connection to your MetaTrader account."
    commands = "List of commands:\n/start : displays welcome message\n/help : displays list of commands and example trades\n/trade : takes in user inputted trade for parsing and placement\n/calculate : calculates trade information for a user inputted trade"
    trade_example = "Example Trades 💴:\n\n"
    market_execution_example = "Market Execution:\nBUY GBPUSD\nEntry NOW\nSL 1.14336\nTP 1.28930\nTP 1.29845\n\n"
    limit_example = "Limit Execution:\nBUY LIMIT GBPUSD\nEntry 1.14480\nSL 1.14336\nTP 1.28930\n\n"
    note = "You are able to enter up to two take profits. If two are entered, both trades will use half of the position size, and one will use TP1 while the other uses TP2.\n\nNote: Use 'NOW' as the entry to enter a market execution trade."

    # sends messages to user
    update.effective_message.reply_text(help_message)
    update.effective_message.reply_text(commands)
    update.effective_message.reply_text(trade_example + market_execution_example + limit_example + note)

    return

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation.   
    
    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    update.effective_message.reply_text("Command has been canceled.")

    # removes trade from user context data
    if context.user_data['trade'] is not None:
        context.user_data['trade'] = None

    return ConversationHandler.END

def error(update: Update, context: CallbackContext) -> None:
    """Logs Errors caused by updates.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    logger.warning('Update "%s" caused error "%s"', update, context.error)

    return

def Trade_Command(update: Update, context: CallbackContext) -> int:
    """Asks user to enter the trade they would like to place.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)and not(update.effective_message.chat.username == CHANNEL_USER)):
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return ConversationHandler.END
    
    # initializes the user's trade as empty prior to input and parsing
    if context.user_data['trade'] is not None:
        context.user_data['trade'] = None
    
    # asks user to enter the trade
    update.effective_message.reply_text("Please enter the trade that you would like to place.")

    return TRADE

def Calculation_Command(update: Update, context: CallbackContext) -> int:
    """Asks user to enter the trade they would like to calculate trade information for.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if(not(update.effective_message.chat.username == TELEGRAM_USER)and not(update.effective_message.chat.username == CHANNEL_USER)):
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return ConversationHandler.END

    # initializes the user's trade as empty prior to input and parsing
    if context.user_data['trade'] is not None:
        context.user_data['trade'] = None

    # asks user to enter the trade
    update.effective_message.reply_text("Please enter the trade that you would like to calculate.")

    return CALCULATE

 # Function for handle message
def TotalMessHandle(update: Update, context: CallbackContext)-> int:
    checktruesignal = CheckSignalMessage(update.effective_message.text)
    temp = Trade_Command
    if temp == TRADE and checktruesignal == TRADE :
        PlaceTrade
    return TRADE

# Function for check message is a signal format true
def CheckSignalMessage(signal:str)-> int:
    # extracts symbolplus '/' from trade signal if found then replace '/' to ''
    for elemental in SYMBOLSPLUS:
        calcusymbol = signal[0].upper().find(elemental,0)
        if(calcusymbol != -1):          
            return TRADE   
   # extracts symbol from trade signal                      
    for element in SYMBOLS:
        calcu = signal[0].upper().find(element,0)
        if(calcu != -1):
            return TRADE
    return ERROR
    

def main() -> None:
    """Runs the Telegram bot."""

    updater = Updater(TOKEN, use_context=True)

    # get the dispatcher to register handlers
    dp = updater.dispatcher

    # message handler
    dp.add_handler(CommandHandler("start", welcome))

    # help command handler
    dp.add_handler(CommandHandler("help", help))

    """conv_handler = ConversationHandler(
        entry_points=[CommandHandler("trade", Trade_Command), CommandHandler("calculate", Calculation_Command)],
        states={
            TRADE: [MessageHandler(Filters.text & ~Filters.command, PlaceTrade)],
            CALCULATE: [MessageHandler(Filters.text & ~Filters.command, CalculateTrade)],
            DECISION: [CommandHandler("yes", PlaceTrade), CommandHandler("no", cancel)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )"""

    # conversation handler for entering trade or calculating trade information
    """dp.add_handler(conv_handler)"""

    # message handler for all messages that are not included in conversation handler
    """"dp.add_handler(MessageHandler(Filters.text, unknown_command))"""
    """"dp.add_handler(MessageHandler(Filters.text,TotalMessHandle()))"""
    dp.add_handler(MessageHandler(Filters.text, TotalMessHandle))

    # log all errors
    dp.add_error_handler(error)
    
    # listens for incoming updates from Telegram
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=APP_URL + TOKEN)
    updater.idle()

    return


if __name__ == '__main__':
    main()
