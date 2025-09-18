# Advanced Machine Co. MRP Web Dashboard

A simple web interface for managing work orders, certificates of completion (COCs), and purchase orders (POs) in the Advanced Machine Co. Manufacturing Resource Planning system.

## Features

### 3 Main Dashboard Sections

1. **Live Orders** - View and manage active work orders
   - View open orders sorted from newest to oldest
   - See order details, customer, part information, and progress
   - Create purchase orders for BOM processes
   - View detailed order information including BOM processes

2. **Recent Completed Orders** (Last 30 days)
   - Generate Certificates of Completion (COCs)
   - Track payment status (Not Received, In Progress, Received)
   - Download generated COC PDFs
   - Update payment status with dropdown menu

3. **Old Orders** (Older than 30 days)
   - Historical order management
   - View completed orders and their status
   - Download existing COC documents

## Key Functionality

- **COC Generation**: Generate certificates of completion using the existing `cocGenerate.py`
- **PO Creation**: Create purchase orders using the existing `poGenerate.py`
- **Payment Tracking**: Track payment status for completed orders
- **Order Details**: View comprehensive order information including BOM processes
- **PDF Downloads**: Download generated COCs and POs
- **Real-time Updates**: Dashboard updates automatically after actions

## Installation & Setup

### One-Command Setup

Simply run Docker Compose from the project root directory:

```bash
docker-compose up -d
```

This automatically:
- ✅ **Starts MySQL database** with fresh data
- ✅ **Installs all Python dependencies** (Flask, MySQL connector, etc.)
- ✅ **Initializes database schema** with PaymentStatus column
- ✅ **Installs LibreOffice** for PDF generation
- ✅ **Starts the web dashboard** on port 5000

### Access the Dashboard

Open your browser to: **`http://localhost:5000`**

The dashboard will be ready in about 60 seconds after running `docker-compose up -d`.

## Usage Guide

### Live Orders Section

- **View Details**: Click the eye icon to see comprehensive order information
- **Create PO**: Click the plus icon to create purchase orders for pending BOM processes
- **Order Information**: Shows work order number, customer, part details, quantities, due dates, status, and priority
- **Progress Tracking**: Visual progress indicators and days until due

### Recent Completed Orders Section

- **Generate COC**: Click the certificate icon to generate a Certificate of Completion
- **Update Payment Status**: Use the dropdown menu to update payment status
  - Not Received (red)
  - In Progress (yellow)
  - Received (green)
- **Download COC**: Click the download icon to get the generated COC PDF

### Old Orders Section

- **Historical View**: Browse orders completed more than 30 days ago
- **Download COCs**: Access previously generated certificates
- **Payment Status**: View final payment status for historical orders

## Technical Details

### Architecture

- **Backend**: Flask (Python web framework)
- **Frontend**: Bootstrap 5 with responsive design
- **Database**: MySQL with existing MRP schema
- **Integration**: Direct imports of `cocGenerate.py` and `poGenerate.py`

### Database Integration

- Uses existing MRP database schema
- Adds `PaymentStatus` column to `WorkOrders` table
- Integrates with existing COC and PO generation systems
- Maintains full audit trail and logging


## Security Notes

- No user authentication implemented (as requested)
- File downloads are restricted to the output directory
- SQL injection protection through parameterized queries
- XSS protection through proper HTML escaping

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Ensure Docker containers are running
   - Check database credentials in `run.py`

2. **COC/PO Generation Fails**:
   - Verify template files exist in `DevAssets/` directory
   - Check LibreOffice is installed for PDF conversion
   - Ensure output directory has write permissions

3. **JavaScript Errors**:
   - Check browser console for specific errors
   - Ensure Bootstrap and other CDN resources are loading

### Logs

- Application logs are displayed in the terminal where `run.py` is running
- Database operations are logged with timestamps
- COC and PO generation logs include detailed error information

## Future Enhancements

Potential improvements for future versions:

- User authentication and role-based access
- Advanced filtering and search capabilities
- Bulk operations for multiple orders
- Email notifications for status changes
- Mobile-responsive improvements
- Real-time notifications
- Export capabilities (Excel, CSV)
- Advanced reporting and analytics

## Support

For technical support or feature requests, contact the Advanced Machine Co. IT department.
