# Kopano GRAPI API compatibility with Microsoft Graph

This document summarizes the Kopano GRAPI implementation differences and scope
in relation to Microsoft Graph API. Thus the [upstream documentation](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/overview.md) applies to GRAPI. For a list of endpoints implemented by GRAPI
see the [Resources](#Resources) section below.

## What's noteworthy

- Endpoints such as "/me/messages" or "/me/events" do not expose the entire
  store, but just the inbox or calendar, respectively.
- Relative paths, such as "mailFolder/id/childFolder/id/childFolder/id/.." are
  not supported.

## Query Parameters

Genereally the [Graph documentation](https://developer.microsoft.com/en-us/graph/docs/concepts/query_parameters) applies considering the following changes:

- We do not support `$filter` or `$format`.
- Support for `$expand` and `$count` is preliminary.

## Extensions

- We support handling attachments in binary using `$value`.
  For example: `GET /me/messages/id/attachment/id/$value`
- We support the query parameter `$search` for `/users`.

## Batch API

We support the [JSON batching API](https://docs.microsoft.com/en-us/graph/json-batching) for combining multiple requests in one HTTP call.

## Resources

This API supports groupware related endpoints. GRAPI follows a experimental/non-experimental
approach. Experimental endpoints are disabled by default (enable with `--enable-experimental-endpoints`
commandline switch).

### attachment Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/attachment.md)

[Get attachment](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/attachment-get.md)

(Extension: use `attachment/id/$value` to get attachment in binary.)

[Delete attachment](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/attachment-delete.md)

### calendar Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/calendar.md)

[Get calendar](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/calendar-get.md)

[List calendarView](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/calendar-list-calendarview.md)

[List events](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/calendar-list-events.md)

[Create event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/calendar-post-events.md)

[getSchedule](https://docs.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0&tabs=http)

### contact Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/contact.md)

[Get contact](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contact-get.md)

[Delete contact](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contact-delete.md)

[delta](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contact-delta.md)

### contactFolder Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/contactfolder.md)

[Get contactFolder](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contactfolder-get.md)

[List contacts](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contactfolder-list-contacts.md)

[Create contact](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contactfolder-post-contacts.md)

[delta](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/contactfolder-delta.md)

### event Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/event.md)

[Get event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-get.md)

[Update event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-update.md)

[Delete event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-delete.md)

[accept event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-accept.md)

[tentativelyAccept event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-tentativelyaccept.md)

[decline event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-decline.md)

[List instances](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-list-instances.md)

[List attachments](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-list-attachments.md)

[Add attachment](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/event-post-attachments.md)

### group Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/group.md)

[Get group](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/group-get.md)

[List members](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/group-list-members.md)

### mailFolder Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/mailfolder.md)

[Get mailFolder](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-get.md)

[Create childFolder](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-post-childfolders.md)

[List childFolders](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-list-childfolders.md)

[Create message](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-post-messages.md)

[List messages](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-list-messages.md)

[Delete mailFolder](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-delete.md)

[copy](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-copy.md)

[move](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-move.md)

[delta](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/mailfolder-delta.md)

### message Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/message.md)

[Get message](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-get.md)

[Update message](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-update.md)

[Delete message](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-delete.md)

[createReply](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-createreply.md)

[createReplyAll](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-createreplyall.md)

[send](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-send.md)

[List attachments](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-list-attachments.md)

[Add attachment](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-post-attachments.md)

[copy](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-copy.md)

[move](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-move.md)

[delta](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/message-delta.md)

### profilePhoto Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/profilephoto.md)

[Get profilePhoto](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/profilephoto-get.md)

[Update profilePhoto](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/profilephoto-update.md)

### subscription Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/subscription.md)

[Create subscription](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/subscription-post-subscriptions.md)

[Get subscription](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/subscription-get.md)

[Delete subscription](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/subscription-delete.md)

### user Resource

[(Resource)](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/user.md)

[List users](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list.md)

[Get user](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-get.md)

[List messages](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-messages.md)

[Create message](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-post-messages.md)

[List mailFolders](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-mailfolders.md)

[Create mailFolder](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-post-mailfolders.md)

[sendMail](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-sendmail.md)

[List events](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-events.md)

[Create event](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-post-events.md)

[List contactFolders](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-contactfolders.md)

[List calendars](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-calendars.md)

[List calendarView](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-calendarview.md)

[reminderView](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-reminderview.md)

[List contacts](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-contacts.md)

[Create contact](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-post-contacts.md)

[List memberOf](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-list-memberof.md)

[delta](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/api/user-delta.md)

[calendar](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/calendar.md)

[calendars](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/calendar.md)

[events](https://github.com/microsoftgraph/microsoft-graph-docs/blob/master/api-reference/v1.0/resources/event.md)
