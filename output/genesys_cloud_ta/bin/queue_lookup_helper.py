import json

from splunklib import modularinput as smi


def validate_input(definition: smi.ValidationDefinition):
    return

def get_routing_queues(helper, routing_api):
    queue_list = []
    page_number = 1
    try:
        while True:
            queues = routing_api.get_routing_queues(page_size = 500, page_number = page_number)
            for queue in queues.entities:
                queue_list.append(
                    {
                        "id": queue.id,
                        "name": queue.name
                    }
                )
            if not queues.next_uri:
                break 
            else:
                page_number += 1
    except Exception as e:
        helper.log_info(f"Error when calling RoutingApi->get_routing_queues: {e}")
    return queue_list

def stream_events(inputs: smi.InputDefinition, ew: smi.EventWriter):
    input_items = [{'count': len(inputs.inputs)}]
    for input_name, input_item in inputs.inputs.items():
        input_item['name'] = input_name
        input_items.append(input_item)
    event = smi.Event(
        data=json.dumps(input_items),
        sourcetype='queue_lookup',
    )
    ew.write_event(event)