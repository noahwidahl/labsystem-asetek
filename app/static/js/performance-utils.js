// Performance utilities for the lab system

/**
 * Debounce function to limit API calls during search/filter operations
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Simple caching mechanism for API responses
 */
class SimpleCache {
    constructor(maxSize = 50, maxAge = 5 * 60 * 1000) { // 5 minutes default
        this.cache = new Map();
        this.maxSize = maxSize;
        this.maxAge = maxAge;
    }

    set(key, value) {
        // Remove oldest entries if cache is full
        if (this.cache.size >= this.maxSize) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        
        this.cache.set(key, {
            data: value,
            timestamp: Date.now()
        });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        // Check if item has expired
        if (Date.now() - item.timestamp > this.maxAge) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }

    clear() {
        this.cache.clear();
    }
}

/**
 * Virtual scrolling for large tables
 */
class VirtualTable {
    constructor(container, data, itemHeight = 50, renderItem) {
        this.container = container;
        this.data = data;
        this.itemHeight = itemHeight;
        this.renderItem = renderItem;
        this.visibleItems = Math.ceil(container.clientHeight / itemHeight) + 5; // Buffer
        this.startIndex = 0;
        
        this.init();
    }

    init() {
        this.container.style.position = 'relative';
        this.container.style.overflow = 'auto';
        
        // Create spacers for virtual scrolling
        this.topSpacer = document.createElement('div');
        this.bottomSpacer = document.createElement('div');
        
        this.container.appendChild(this.topSpacer);
        this.container.appendChild(this.bottomSpacer);
        
        this.container.addEventListener('scroll', debounce(() => this.onScroll(), 10));
        this.render();
    }

    onScroll() {
        const scrollTop = this.container.scrollTop;
        this.startIndex = Math.floor(scrollTop / this.itemHeight);
        this.render();
    }

    render() {
        const endIndex = Math.min(this.startIndex + this.visibleItems, this.data.length);
        
        // Update spacers
        this.topSpacer.style.height = `${this.startIndex * this.itemHeight}px`;
        this.bottomSpacer.style.height = `${(this.data.length - endIndex) * this.itemHeight}px`;
        
        // Clear existing items (except spacers)
        const children = Array.from(this.container.children);
        children.forEach(child => {
            if (child !== this.topSpacer && child !== this.bottomSpacer) {
                child.remove();
            }
        });
        
        // Render visible items
        for (let i = this.startIndex; i < endIndex; i++) {
            const item = this.renderItem(this.data[i], i);
            this.container.insertBefore(item, this.bottomSpacer);
        }
    }

    updateData(newData) {
        this.data = newData;
        this.render();
    }
}

/**
 * Lazy loading image utility
 */
function setupLazyLoading() {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

/**
 * Batch API requests to reduce server load
 */
class RequestBatcher {
    constructor(delay = 100) {
        this.delay = delay;
        this.queue = [];
        this.timer = null;
    }

    add(url, options = {}) {
        return new Promise((resolve, reject) => {
            this.queue.push({ url, options, resolve, reject });
            
            if (this.timer) {
                clearTimeout(this.timer);
            }
            
            this.timer = setTimeout(() => this.flush(), this.delay);
        });
    }

    async flush() {
        if (this.queue.length === 0) return;
        
        const requests = this.queue.splice(0);
        
        try {
            const responses = await Promise.all(
                requests.map(req => fetch(req.url, req.options))
            );
            
            const results = await Promise.all(
                responses.map(res => res.json())
            );
            
            requests.forEach((req, index) => {
                req.resolve(results[index]);
            });
        } catch (error) {
            requests.forEach(req => req.reject(error));
        }
    }
}

// Global instances
window.apiCache = new SimpleCache();
window.requestBatcher = new RequestBatcher();

// Initialize performance optimizations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setupLazyLoading();
});

// Export utilities
window.PerformanceUtils = {
    debounce,
    SimpleCache,
    VirtualTable,
    setupLazyLoading,
    RequestBatcher
};