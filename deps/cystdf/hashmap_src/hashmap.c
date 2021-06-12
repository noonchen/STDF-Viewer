/*
 * from : https://gist.github.com/warmwaffles/6fb6786be7c86ed51fce
 * Generic hashmap manipulation functions
 * SEE: http://elliottback.com/wp/hashmap-implementation-in-c/
 */

/*
 * Generic map implementation. This class is thread-safe.
 * free() must be invoked when only one thread has access to the hashmap.
 */

#include <stdlib.h>
#include "hashmap.h"


#define INITIAL_SIZE 512

// We need to keep keys and values
typedef struct _hashmap_element{
    uint32_t key;
    uint8_t in_use;
    uint32_t data;
} hashmap_element;

// A hashmap has some maximum size and current size,
// as well as the data to hold.
typedef struct _hashmap_map{
    int table_size;
    int size;
    hashmap_element *data;
} hashmap_map;

/*
 * Return an empty hashmap, or NULL on failure.
 */
map_t hashmap_new(int size) {
    if (size <= 0) {
        size = INITIAL_SIZE;
    }
    hashmap_map* m = (hashmap_map*) malloc(sizeof(hashmap_map));
    if(!m) goto err;

    m->data = (hashmap_element*) calloc(size, sizeof(hashmap_element));
    if(!m->data) goto err;

    m->table_size = size;
    m->size = 0;

    return m;
    err:
        if (m)
            hashmap_free(m);
        return NULL;
}

/*
 * Hashing function for an integer
 */
uint32_t hashmap_hash_int(hashmap_map * m, uint32_t key){
    /* Robert Jenkins' 32 bit Mix Function */
    key += (key << 12);
    key ^= (key >> 22);
    key += (key << 4);
    key ^= (key >> 9);
    key += (key << 10);
    key ^= (key >> 2);
    key += (key << 7);
    key ^= (key >> 12);

    /* Knuth's Multiplicative Method */
    key = (key >> 3) * 2654435761;

    return key % m->table_size;
}

/*
 * Return the integer of the location in data
 * to store the point to the item, or MAP_FULL.
 */
int hashmap_hash(map_t in, uint32_t key, uint32_t* p_curr){
    uint32_t curr;

    /* Cast the hashmap */
    hashmap_map* m = (hashmap_map *) in;

    /* If full, return immediately */
    if(m->size == m->table_size) return MAP_FULL;

    /* Find the best index */
    curr = hashmap_hash_int(m, key);
    /* Linear probling */
    for(int i = 0; i< m->table_size; i++){
        if(m->data[curr].in_use == 0){
            // if location is not used, return this location
            *p_curr = curr;
            return MAP_OK;
        }
        if(m->data[curr].key == key && m->data[curr].in_use == 1){
            // if location is used, and key is the same, return this location for replacing
            *p_curr = curr;
            return MAP_OK;
        }
        // if collison is found, manually search for the next location
        curr = (curr + 1) % m->table_size;
    }
    return MAP_FULL;
}

/*
 * Doubles the size of the hashmap, and rehashes all the elements
 */
int hashmap_rehash(map_t in){
    int status = MAP_OK;
    int old_size;
    hashmap_element* curr;

    /* Setup the new elements */
    hashmap_map *m = (hashmap_map *) in;
    hashmap_element* temp = (hashmap_element *)
        calloc(2 * m->table_size, sizeof(hashmap_element));
    if(!temp) return MAP_OMEM;

    /* Update the array */
    curr = m->data;
    m->data = temp;

    /* Update the size */
    old_size = m->table_size;
    m->table_size = 2 * m->table_size;
    m->size = 0;

    /* Rehash the elements */
    for(int i = 0; i < old_size; i++){
        status = hashmap_put(m, curr[i].key, curr[i].data);
        if (status != MAP_OK)
            break;
    }
    free(curr);

    return (status != MAP_OK)? status : MAP_OK;
}

/*
 * Add a pointer to the hashmap with some key
 */
int hashmap_put(map_t in, uint32_t key, uint32_t value){
    uint32_t index;
    hashmap_map* m;
    int status;

    /* Cast the hashmap */
    m = (hashmap_map *) in;
    /* Find a place to put our value */
    status = hashmap_hash(in, key, &index);
    if (status == MAP_FULL) {
        if (hashmap_rehash(in) != MAP_OK) {
            return MAP_OMEM;
        }
        status = hashmap_hash(in, key, &index);
        if (status != MAP_OK) {
            return status;
        }
    }
    /* Set the data */
    m->data[index].data = value;
    m->data[index].key = key;
    m->data[index].in_use = 1;
    m->size++;
    return MAP_OK;
}

/*
 * Get your pointer out of the hashmap with a key
 */
int hashmap_get(map_t in, uint32_t key, uint32_t *arg){
    uint32_t curr;
    hashmap_map* m;

    /* Cast the hashmap */
    m = (hashmap_map *) in;

    /* Find data location */
    curr = hashmap_hash_int(m, key);

    /* Linear probing, if necessary */
    for(int i = 0; i< m->table_size; i++){

        if(m->data[curr].key == key && m->data[curr].in_use == 1){
            *arg = m->data[curr].data;
            return MAP_OK;
        }

        curr = (curr + 1) % m->table_size;
    }

    *arg = 0;
    /* Not found */
    return MAP_MISSING;
}

/*
 * Get a random element from the hashmap
 */
// int hashmap_get_one(map_t in, any_t *arg, int remove){
//     int i;
//     hashmap_map* m;

//     /* Cast the hashmap */
//     m = (hashmap_map *) in;

//     /* On empty hashmap return immediately */
//     if (hashmap_length(m) <= 0)
//         return MAP_MISSING;

//     /* Linear probing */
//     for(i = 0; i< m->table_size; i++)
//         if(m->data[i].in_use != 0){
//             *arg = m->data[i].data;
//             if (remove) {
//                 m->data[i].in_use = 0;
//                 m->size--;
//             }
//             return MAP_OK;
//         }

//     return MAP_OK;
// }

/*
 * Iterate the function parameter over each element in the hashmap.  The
 * additional any_t argument is passed to the function as its first
 * argument and the hashmap element is the second.
 */
int hashmap_iterate(map_t in, PFany f, any_t item) {
    /* Cast the hashmap */
    hashmap_map* m = (hashmap_map*) in;

    /* On empty hashmap, return immediately */
    if (hashmap_length(m) <= 0)
        return MAP_MISSING;

    /* Linear probing */
    for(int i = 0; i< m->table_size; i++)
        if(m->data[i].in_use != 0) {
            uint32_t key = m->data[i].key;
            uint32_t data = m->data[i].data;
            int status = f(item, key, data);
            if (status != MAP_OK) {
                return status;
            }
        }

    return MAP_OK;
}

/*
 * check if a key in the map
 */
int hashmap_contains(map_t in, uint32_t key){
    uint32_t curr;
    hashmap_map* m;

    /* Cast the hashmap */
    m = (hashmap_map *) in;
    /* Find key */
    curr = hashmap_hash_int(m, key);

    /* Linear probing, if necessary */
    for(int i = 0; i< m->table_size; i++){
        if(m->data[curr].key == key && m->data[curr].in_use == 1){
            // key is found
            return 1;
        }
        curr = (curr + 1) % m->table_size;
    }

    /* key not found */
    return 0;
}

/*
 * Remove an element with that key from the map
 */
int hashmap_remove(map_t in, uint32_t key){
    uint32_t curr;
    hashmap_map* m;

    /* Cast the hashmap */
    m = (hashmap_map *) in;

    /* Find key */
    curr = hashmap_hash_int(m, key);

    /* Linear probing, if necessary */
    for(int i = 0; i< m->table_size; i++){
        if(m->data[curr].key == key && m->data[curr].in_use == 1){
            /* Blank out the fields */
            m->data[curr].in_use = 0;
            m->data[curr].data = 0;
            m->data[curr].key = 0;

            /* Reduce the size */
            m->size--;
            return MAP_OK;
        }
        curr = (curr + 1) % m->table_size;
    }

    /* Data not found */
    return MAP_MISSING;
}

/* Deallocate the hashmap */
void hashmap_free(map_t in){
    if (in == NULL) {
        return;
    }
    hashmap_map* m = (hashmap_map*) in;
    free(m->data);
    free(m);
}

/* Return the length of the hashmap */
int hashmap_length(map_t in){
    hashmap_map* m = (hashmap_map *) in;
    if(m != NULL) return m->size;
    else return 0;
}