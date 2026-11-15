package tn.esprit.awd.candidature.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import tn.esprit.awd.candidature.client.CandidateClient.Candidate;
import tn.esprit.awd.candidature.client.JobClient.Job;
import tn.esprit.awd.candidature.entity.Application;
import tn.esprit.awd.candidature.entity.Application.Status;
import tn.esprit.awd.candidature.entity.ApplicationEvent;
import tn.esprit.awd.candidature.repository.ApplicationEventRepository;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
public class ApplicationEvents {
    private static final String EXCHANGE = "jobboard.exchange";
    private static final Logger LOG = LoggerFactory.getLogger(ApplicationEvents.class);

    private final ApplicationEventRepository outbox;
    private final ObjectMapper json;
    private final RabbitTemplate rabbit;

    public ApplicationEvents(ApplicationEventRepository outbox, ObjectMapper json, RabbitTemplate rabbit) {
        this.outbox = outbox;
        this.json = json;
        this.rabbit = rabbit;
    }

    @Bean
    TopicExchange applicationEventsExchange() {
        return new TopicExchange(EXCHANGE);
    }

    void created(Application application, Candidate candidate, Job job) {
        var payload = event("ApplicationCreated", application, candidate);
        payload.put("jobTitle", job.name());
        enqueue("application.created", payload);
    }

    void statusChanged(Application application, Status previous, Candidate candidate) {
        var payload = event("ApplicationStatusChanged", application, candidate);
        payload.put("fromStatus", previous);
        payload.put("toStatus", application.getStatus());
        enqueue("application.status.changed", payload);
    }

    private Map<String, Object> event(String type, Application application, Candidate candidate) {
        var payload = new LinkedHashMap<String, Object>();
        payload.put("eventId", UUID.randomUUID());
        payload.put("eventType", type);
        payload.put("applicationId", application.getId());
        payload.put("candidateId", application.getCandidateId());
        payload.put("jobId", application.getJobId());
        payload.put("email", candidate.email());
        payload.put("candidateName", candidate.fullName());
        payload.put("occurredAt", Instant.now().toString());
        return payload;
    }

    private void enqueue(String routingKey, Map<String, Object> payload) {
        try {
            outbox.save(new ApplicationEvent(routingKey, json.writeValueAsString(payload)));
        } catch (JsonProcessingException failure) {
            throw new IllegalStateException("Could not serialize application event", failure);
        }
    }

    @Scheduled(fixedDelayString = "${application.outbox.delay-ms:5000}")
    public void deliverPending() {
        for (var event : outbox.findTop50ByOrderByIdAsc()) {
            try {
                var message = MessageBuilder.withBody(event.getPayload().getBytes(StandardCharsets.UTF_8))
                        .setContentType(MessageProperties.CONTENT_TYPE_JSON)
                        .setDeliveryMode(MessageDeliveryMode.PERSISTENT)
                        .build();
                var correlation = new CorrelationData();
                rabbit.send(EXCHANGE, event.getRoutingKey(), message, correlation);
                var confirmation = correlation.getFuture().get(5, TimeUnit.SECONDS);
                if (!confirmation.isAck() || correlation.getReturned() != null) {
                    LOG.warn("Broker did not route application event {}. Delivery will be retried.", event.getId());
                    return;
                }
                outbox.deleteById(event.getId());
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return;
            } catch (ExecutionException | TimeoutException | RuntimeException failure) {
                LOG.warn("Delivery of application event {} will be retried: {}", event.getId(), failure.getMessage());
                return;
            }
        }
    }
}
