def clean_email(email):
    # Fix gmail mispellings
    try:
        domain_part = email_str.split('@')[1]

        if (domain_part.startswith('gm') or (domain_part.startswith('g') and domain_part.endswith('il.com'))) and len(domain_part) <= 11 and domain_part != 'gmail.com':
            email_str = email_str.replace(domain_part, 'gmail.com')
            print(domain_part)
    except:
        return email_str

    return email_str


def validate_email(email_column):
    """
    Validate email addresses in a pandas Series.
    
    Parameters:
    -----------
    email_column : pd.Series
        Series containing email addresses to validate
    
    Returns:
    --------
    pd.Series
        Boolean Series indicating email validity (True = valid, False = invalid)
    """
    
    # Email regex pattern - covers most common valid email formats
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Initial regex validation
    regex_valid = email_column.str.match(email_pattern, na=False)
    
    # Additional validation for edge cases
    def additional_validation(email):
        email = email.lower()

        if email == '(empty)':
            return False

        # Check for consecutive dots
        if '..' in email:
            return False
            
        # Must contain exactly one @
        if email.count('@') != 1:
            return False
            
        # Check if starts or ends with dot in local part
        local_part = email.split('@')[0]
        if local_part.startswith('.') or local_part.endswith('.'):
            return False
            
        # Check domain part
        domain_part = email.split('@')[1]
        if domain_part.startswith('.') or domain_part.endswith('.'):
            return False
        if domain_part == 'gmail' and len(local_part) < 6:
            return False
            
        return True
    
    # Apply additional validation
    additional_valid = email_column.apply(additional_validation)
    
    # Combine both validations
    email_validity = regex_valid & additional_valid
    
    return email_validity


def clean_phone(phone):   
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) == 0:
        return ''

    # Handle Vietnamese country code
    if digits_only.startswith('84'):
        if len(digits_only) == 11:
            return '+84' + digits_only[2:]
        elif len(digits_only) == 12: # 840xxxxxxxxx
            return '+84' + digits_only[3:]
        elif len(digits_only) == 9: # +8484xxxxxxx
            return '+84' + digits_only
    # Handle wrong country code
    elif digits_only.startswith('1'):
        if len(digits_only) == 10:
            return '+84' + digits_only[1:]
        elif len(digits_only) == 11: # 10xxxxxxxxx
            return '+84' + digits_only[2:]
    elif digits_only.startswith('0'):
        return '+84' + digits_only[1:]
    elif len(digits_only) > 0:
        return '+84' + digits_only
    
    return phone


def validate_phone(phone):
    """
    Validate Vietnamese phone numbers in a pandas Series.

    Vietnamese phone number rules:
    - Mobile: 10 digits starting with 03, 05, 07, 08, 09
    - Country code: +84 or 84

    Parameters:
        phone: Vietnamese phone numbers as strings

    Returns:
        Boolean indicating phone validity (True = valid, False = invalid)
    """        

    if phone == '':
        return False
    
    # Validate length (must be 12 digits for Vietnamese numbers)
    if len(phone) != 12:
        return False

    # Check if it starts with +84 (Vietnamese numbers start with +84)
    if not phone.startswith('+84'):
        return False
    
    # Valid Vietnamese mobile prefixes (first 2 digits)
    valid_mobile_prefixes = ['3', '5', '7', '8', '9']
    # Validate prefix
    prefix = phone[3:4]        
    if prefix not in valid_mobile_prefixes:
        return False
    
    return True