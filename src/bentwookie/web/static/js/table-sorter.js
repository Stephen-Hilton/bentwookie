/**
 * TableSorter - Client-side table sorting functionality
 * 
 * Feature: bentwookie-web-ui-enhancements
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.6
 */

class TableSorter {
    /**
     * Create a TableSorter instance for a table element.
     * @param {HTMLTableElement} tableElement - The table to make sortable
     */
    constructor(tableElement) {
        this.table = tableElement;
        this.sortState = {
            column: null,
            direction: 'asc'
        };
        this.originalRows = [];
    }

    /**
     * Initialize sorting on all sortable columns.
     */
    init() {
        if (!this.table) return;

        const headers = this.table.querySelectorAll('th[data-sortable="true"]');
        const tbody = this.table.querySelector('tbody');
        
        if (!tbody) return;

        // Store original row order for reset capability
        this.originalRows = Array.from(tbody.querySelectorAll('tr'));

        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.classList.add('sortable-header');
            
            // Add sort indicator span if not present
            if (!header.querySelector('.sort-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'sort-indicator';
                indicator.innerHTML = ' ⇅';
                header.appendChild(indicator);
            }

            header.addEventListener('click', () => {
                this.handleHeaderClick(header, index);
            });
        });
    }

    /**
     * Handle click on a sortable header.
     * @param {HTMLTableCellElement} header - The clicked header
     * @param {number} columnIndex - The column index
     */
    handleHeaderClick(header, columnIndex) {
        // Determine new sort direction
        let newDirection = 'asc';
        if (this.sortState.column === columnIndex) {
            newDirection = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        }

        this.sortByColumn(columnIndex, newDirection);
        this.updateSortIndicators(header, newDirection);
    }

    /**
     * Sort table by specified column index.
     * @param {number} columnIndex - The column to sort by
     * @param {'asc' | 'desc'} direction - Sort direction
     */
    sortByColumn(columnIndex, direction) {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        const header = this.table.querySelectorAll('th')[columnIndex];
        const sortType = header?.getAttribute('data-sort-type') || 'text';

        rows.sort((rowA, rowB) => {
            const cellA = rowA.querySelectorAll('td')[columnIndex];
            const cellB = rowB.querySelectorAll('td')[columnIndex];

            if (!cellA || !cellB) return 0;

            // Get sort value from data attribute or text content
            const valueA = cellA.getAttribute('data-sort-value') || cellA.textContent.trim();
            const valueB = cellB.getAttribute('data-sort-value') || cellB.textContent.trim();

            let comparison = this.compareValues(valueA, valueB, sortType);
            
            return direction === 'desc' ? -comparison : comparison;
        });

        // Re-append rows in sorted order
        rows.forEach(row => tbody.appendChild(row));

        // Update sort state
        this.sortState = { column: columnIndex, direction };
    }

    /**
     * Compare two values based on data type.
     * @param {string} a - First value
     * @param {string} b - Second value
     * @param {'text' | 'number' | 'date'} type - Data type for comparison
     * @returns {number} Comparison result (-1, 0, or 1)
     */
    compareValues(a, b, type) {
        // Handle empty/null values - push to end
        if (!a && !b) return 0;
        if (!a) return 1;
        if (!b) return -1;

        switch (type) {
            case 'number':
                const numA = parseFloat(a) || 0;
                const numB = parseFloat(b) || 0;
                return numA - numB;

            case 'date':
                const dateA = new Date(a);
                const dateB = new Date(b);
                // Handle invalid dates
                if (isNaN(dateA.getTime()) && isNaN(dateB.getTime())) return 0;
                if (isNaN(dateA.getTime())) return 1;
                if (isNaN(dateB.getTime())) return -1;
                return dateA.getTime() - dateB.getTime();

            case 'text':
            default:
                return a.localeCompare(b, undefined, { sensitivity: 'base' });
        }
    }

    /**
     * Update sort indicators on headers.
     * @param {HTMLTableCellElement} activeHeader - The currently sorted header
     * @param {'asc' | 'desc'} direction - Current sort direction
     */
    updateSortIndicators(activeHeader, direction) {
        // Remove sort classes from all headers
        const allHeaders = this.table.querySelectorAll('th[data-sortable="true"]');
        allHeaders.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            const indicator = header.querySelector('.sort-indicator');
            if (indicator) {
                indicator.innerHTML = ' ⇅';
            }
        });

        // Add sort class to active header
        activeHeader.classList.add(`sort-${direction}`);
        const activeIndicator = activeHeader.querySelector('.sort-indicator');
        if (activeIndicator) {
            activeIndicator.innerHTML = direction === 'asc' ? ' ↑' : ' ↓';
        }
    }

    /**
     * Get current sort state.
     * @returns {{ column: number | null, direction: 'asc' | 'desc' }}
     */
    getSortState() {
        return { ...this.sortState };
    }

    /**
     * Reset table to original row order.
     */
    reset() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody || this.originalRows.length === 0) return;

        this.originalRows.forEach(row => tbody.appendChild(row));
        this.sortState = { column: null, direction: 'asc' };

        // Reset all indicators
        const allHeaders = this.table.querySelectorAll('th[data-sortable="true"]');
        allHeaders.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            const indicator = header.querySelector('.sort-indicator');
            if (indicator) {
                indicator.innerHTML = ' ⇅';
            }
        });
    }
}

/**
 * Initialize TableSorter on all tables with data-sortable-table attribute.
 */
function initTableSorters() {
    const tables = document.querySelectorAll('table[data-sortable-table="true"]');
    tables.forEach(table => {
        const sorter = new TableSorter(table);
        sorter.init();
        // Store reference on table element for potential later access
        table._tableSorter = sorter;
    });
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTableSorters);
} else {
    initTableSorters();
}
