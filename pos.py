from Tkinter import *
import csv
import serial
import time

class App:

    itemListFormat = "{:<24} ${:<8} {:<}"
    currentTransArray = []
    dayList = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    serialPort = "ACM0"
    itemDataFilePath = "/home/pi/pos/itemData.csv"
    dataFilePath = "/home/pi/pos/data.csv"

    def __init__(self, root):
        def key(event):
            self.enterItem()
            self.updateStatsBox("Fri")

        root.title("Robostorm POS")

        self.leftStuffFrame = Frame(root)
        self.rightStuffFrame = Frame(root)
        self.itemStatsFrame = Frame(root)
        self.cashDrawerFrame = Frame(root)


        self.itemListScroll = Scrollbar(self.leftStuffFrame, orient=VERTICAL)
        self.itemList = Listbox(self.leftStuffFrame, selectmode=EXTENDED, height=15, width=40, font=("Monospace", 10), yscrollcommand=self.itemListScroll.set)
        self.itemListScroll.config(command=self.itemList.yview)
        self.itemListScroll.pack(side=RIGHT, fill=Y)

        self.barcodeEntry = Entry(self.leftStuffFrame)
        self.barcodeEntry.focus_set()
        self.barcodeEntry.bind("<Return>", key)

        self.statusBox = Listbox(self.leftStuffFrame, height=1, width=30)
        self.statusBox.insert(0, "POS Started")

        self.itemList.pack()
        self.barcodeEntry.pack(anchor=W)
        self.statusBox.pack(anchor=W)




        self.insertItemFrame = Frame(self.rightStuffFrame, padx = 10, bd=2, relief=RIDGE)

        itemListOptions = self.getItemList()
        self.itemOptionVar = StringVar(root)
        self.itemOptionVar.set(itemListOptions[0])
        self.insertItemMenu = OptionMenu(self.insertItemFrame, self.itemOptionVar, *itemListOptions)

        self.itemQtyFrame = Frame(self.insertItemFrame)

        self.itemQtyLabel = Label(self.itemQtyFrame, text="Quantity")

        self.itemQtyEntry = Spinbox(self.itemQtyFrame, width=3, from_=1, to=100)

        self.itemQtyLabel.grid(row=0, column=0)
        self.itemQtyEntry.grid(row=0, column=1)

        self.insertItemButton = Button(self.insertItemFrame, text="Insert Item", command=self.enterItemManual)

        self.insertItemMenu.pack()
        self.itemQtyFrame.pack()
        self.insertItemButton.pack()


        self.deleteButtonFrame = Frame(self.rightStuffFrame, bd=2, relief=RIDGE)
        
        self.deleteSelectedButton = Button(self.deleteButtonFrame, text="Delete Selected Items", command=self.deleteSelectedItem)
        self.deleteSelectedButton.pack()

        self.deleteLastButton = Button(self.deleteButtonFrame, text="Delete Last Item", command=self.deleteLastItem)
        self.deleteLastButton.pack()


        self.transactionFrame = Frame(self.rightStuffFrame, bd=2, relief=RIDGE)

        self.transactionAmount = StringVar()
        self.transactionAmountLabel = Label(self.transactionFrame, textvariable=self.transactionAmount, bg="yellow")
        self.transactionAmountLabel.pack()
        self.updateTransactionAmount()

        self.enterButton = Button(self.transactionFrame, text="Apply Transaction", command=self.enterTransaction)
        self.enterButton.pack()

        self.insertItemFrame.pack(pady=10, anchor=N)
        self.deleteButtonFrame.pack(pady=10)
        self.transactionFrame.pack(pady=10)



        self.dayOptionVar = StringVar(root)
        self.dayOptionVar.set(self.dayList[0])
        self.dayMenu = OptionMenu(self.itemStatsFrame, self.dayOptionVar, *self.dayList, command=self.updateStatsBox)

        self.itemStatsScroll = Scrollbar(self.itemStatsFrame, orient=VERTICAL)
        self.itemStatsBox = Listbox(self.itemStatsFrame, height=16, width=50, font=("Monospace", 9), yscrollcommand=self.itemStatsScroll.set)
        self.itemStatsScroll.config(command=self.itemList.yview)
        self.itemStatsScroll.pack(side=RIGHT, fill=Y)
        self.updateStatsBox(self.dayOptionVar.get())

        self.dayMenu.pack()
        self.itemStatsBox.pack()


        self.portLabel = Label(self.cashDrawerFrame, text="Cash Drawer Serial Port")

        self.portEntry = Entry(self.cashDrawerFrame, width=10)

        self.portButton = Button(self.cashDrawerFrame, text="Set", command=self.setSerialPort)

        self.portLabel.pack()
        self.portEntry.pack()
        self.portButton.pack()
        
        

        self.leftStuffFrame.grid(row=0, column=0)
        self.rightStuffFrame.grid(row=0, column=1)
        self.itemStatsFrame.grid(row=0, column=2)
        self.cashDrawerFrame.grid(row=0, column=3)

    def enterItem(self):
        barcode = self.barcodeEntry.get()
        adminCode = "admin"

        if not barcode == "":
            self.barcodeEntry.delete(0, END)

            if barcode == adminCode:
                self.openDrawer()
            else:
                itemInfoList = self.getItemInfo(barcode, "barcode")

                if itemInfoList == []:
                    self.statusBox.insert(0, "Error: Not a valid barcode")
                else:
                    self.itemList.insert(END, self.itemListFormat.format(*itemInfoList, sp=" "))
                    self.currentTransArray.insert(len(self.currentTransArray), itemInfoList[0])
                    self.statusBox.insert(0, "Item: " + itemInfoList[0] + " Entered")
                    self.updateTransactionAmount()

    def enterItemManual(self):
        itemName = self.itemOptionVar.get()
        itemQty = self.itemQtyEntry.get()

        self.itemQtyEntry.delete(0, END)

        itemInfoList = self.getItemInfo(itemName, "name")

        if itemQty == "":
            itemQty = "1"

        for item in range(0, int(itemQty)):
            self.itemList.insert(END, self.itemListFormat.format(*itemInfoList, sp=" "))
            self.currentTransArray.insert(len(self.currentTransArray), itemName)
        self.statusBox.insert(0, "Item: " + itemName + ", Qty " + itemQty + " Entered")
        self.updateTransactionAmount()

    def deleteLastItem(self):
        if not self.currentTransArray == []:
            self.itemList.delete(END)
            self.currentTransArray = self.currentTransArray[:-1]
            self.statusBox.insert(0, "Last Item Deleted")
            self.updateTransactionAmount()
        else:
            self.statusBox.insert(0, "Error: No Items to Delete")

    def deleteSelectedItem(self):
        for i in self.itemList.curselection()[::-1]:
            self.itemList.delete(i)
            del self.currentTransArray[i]
            self.statusBox.insert(0, "Selected Item(s) Deleted")
            self.updateTransactionAmount()

    def getItemInfo(self, ident, identType):
        itemInfoList = []
        with open(self.itemDataFilePath) as itemDataFile:
            itemData = csv.reader(itemDataFile, delimiter=',')
            for item in itemData:
                if (identType == "barcode" and item[2] == ident) or (identType == "name" and item[0] == ident):
                    itemInfoList = [item[0], item[1], item[2]]
        return itemInfoList

    def getItemList(self):
        itemList = []
        with open(self.itemDataFilePath) as itemDataFile:
            itemData = csv.reader(itemDataFile, delimiter=',')
            for item in itemData:
                itemList.insert(len(itemList), item[0])
        return itemList

#    def getDayList(self):
#        dayList = []
#        dayTypes = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
#        with open('data.csv') as dataFile:
#            data = csv.reader(dataFile, delimiter=',')
#            for line in data:
#                lineStr = ''.join(line)
#                print(lineStr[:3])
#                if lineStr[:3] in dayTypes:
#                    dayList.insert(len(dayList), lineStr[:3])
#        if dayList == []:
#            dayList.insert(0, "None")
#        return dayList

    def enterTransaction(self):
        if not self.currentTransArray == []:
            with open(self.dataFilePath, "a") as dataFile:
                data = csv.writer(dataFile, delimiter=',')
                #data.writerow([time.asctime(time.localtime(time.time()))])
                #for item in self.currentTransArray:
                #    data.writerow([item])
                #data.writerow([])
                dataRow = [time.asctime(time.localtime(time.time()))]
                for item in self.currentTransArray:
                    dataRow.insert(len(dataRow), item)
                data.writerow(dataRow)
            self.currentTransArray = []
            self.itemList.delete(0, END)
            self.statusBox.insert(0, "Transaction Completed")
            self.updateTransactionAmount()
            self.updateStatsBox(self.dayOptionVar.get())
            self.openDrawer()
        else:
            self.statusBox.insert(0, "Error: No items to transact")

    def updateTransactionAmount(self):
        amount = 0
        for item in self.currentTransArray:
            itemInfoList = self.getItemInfo(item, "name")
            amount += int(itemInfoList[1])
        self.transactionAmount.set("Transaction Amount: $" + str(amount))

    def updateStatsBox(self, day):
        itemNameList = self.getItemList()
        itemStatsFormat = "{:<24} ${:<8} {:<8} ${:<8}"
        totalDayMoney = 0
        self.itemStatsBox.delete(0, END)
        #with open('data.csv') as dataFile:
            #data = csv.reader(dataFile, delimiter=',')
            #for line in data:
            #    lineStr = ''.join(line)
            #    if lineStr[:3] == day:
            #        for 

        #for name in itemNameList:
        #    nameAmount = 0
        #    with open('data.csv') as dataFile:
        #        data = csv.reader(dataFile, delimiter=',')
        #        for item in data:
        #            if item == [name]:
        #                nameAmount += 1
        #        nameInfo = self.getItemInfo(name, "name")
        #        nameCost = nameInfo[1]
        #        totalNameCost = int(nameCost) * nameAmount
        #        totalMoney += totalNameCost
        #        nameData = [name, nameCost, nameAmount, totalNameCost]
        #        self.itemStatsBox.insert(END, itemStatsFormat.format(*nameData, sp=" "))
        #self.itemStatsBox.insert(END, "Total: $" + str(totalMoney))

        for name in itemNameList:
            nameAmount = 0
            with open(self.dataFilePath) as dataFile:
                data = csv.reader(dataFile, delimiter=',')
                for line in data:
                    if line[0][:3] == day:
                        for item in line:
                            if item == name:
                                nameAmount += 1
                nameInfo = self.getItemInfo(name, "name")
                nameCost = nameInfo[1]
                totalNameCost = int(nameCost) * nameAmount
                totalDayMoney += totalNameCost
                nameData = [name, nameCost, nameAmount, totalNameCost]
                self.itemStatsBox.insert(END, itemStatsFormat.format(*nameData, sp=" "))
        self.itemStatsBox.insert(END, "Total: $" + str(totalDayMoney))

    def openDrawer(self):
        #port = "/dev/ttyACM0"
        baud = 19200
        data = "d"

        try:
            ser = serial.Serial("/dev/tty" + self.serialPort, baud, timeout=1)
            ser.write(data.encode('ascii'))
        except:
            self.statusBox.insert(0, "Error: Could not open serial")

    def setSerialPort(self):
        self.serialPort = self.portEntry.get()
        self.portEntry.delete(0, END)
        self.statusBox.insert(0, "Serial Port Set as " + self.serialPort)

root = Tk()
app = App(root)
root.mainloop()
