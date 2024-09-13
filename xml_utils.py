import xml.etree.ElementTree as ET
import xml.dom.minidom

# Load the XML file

def write_xml(index,receipt,previous_hash,timestamp,owner,num_investors,marketcap,market_price,token_price,address,amount,currency,name):
    tree = ET.parse('investments.xml')
    root = tree.getroot()
    data_element = root.find('data')
    new_investment = ET.Element('transaction')
    se1 = ET.SubElement(new_investment, 'index')
    se1.text = index # Ensure the text values are strings
    se2 = ET.SubElement(new_investment, 'receipt')
    se2.text = receipt
    se3 = ET.SubElement(new_investment, 'previous_hash')
    se3.text = str(previous_hash)
    se4 = ET.SubElement(new_investment, 'timestamp')
    se4.text = timestamp
    se5 = ET.SubElement(new_investment, 'owner')
    se5.text = owner
    se6 = ET.SubElement(new_investment, 'number_investors')
    se6.text = num_investors
    se7 = ET.SubElement(new_investment, 'marketcap')
    se7.text = marketcap
    se8 = ET.SubElement(new_investment, 'market_price')
    se8.text = market_price
    se9 = ET.SubElement(new_investment, 'tokenized_price')
    se9.text = token_price
    
    ls = ET.SubElement(new_investment, 'ls')
    address = ET.SubElement(ls, 'address')
    address.text = address
    amount = ET.SubElement(ls, 'amount')
    amount.text = amount
    currency = ET.SubElement(ls, 'currency')
    currency.text = currency
    name = ET.SubElement(ls, 'name')
    name.text = name
    receipt = ET.SubElement(ls, 'receipt')
    receipt.text = receipt
    
    # Append the new transaction to the <data> element
    data_element.append(new_investment)
    xml_str = ET.tostring(root, encoding='unicode')
    pretty_xml_str = xml.dom.minidom.parseString(xml_str).toprettyxml()
    # Print the pretty XML
    print(pretty_xml_str)
    # Save the modified XML file
    tree.write('investments.xml')
    