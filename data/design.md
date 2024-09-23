# Data Design

## Entities
* Person
** People are users, but also used for auditing when samples are checked out/in
** Attributes
*** Name - String
*** Username - String
*** ID - Integer
* Sample
** A sample may have multiple items, as it may be a set of tubes containing the same sample
** Attributes
*** Name - String
*** Quantity - Integer
*** Locations - Locations
*** ID - Integer
* StorageDevice
** Like a freezer, but want to leave this flexible
** Attributes
*** ID - Integer
*** 
* Location
** StorageDevice + Slot
** Attributes
*** ID - UUID
*** StorageDevice - StorageDeviceID
*** 