package tn.esprit.awd.candidature.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "application_outbox")
public class ApplicationEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String routingKey;

    @Column(nullable = false, length = 8192)
    private String payload;

    protected ApplicationEvent() {
    }

    public ApplicationEvent(String routingKey, String payload) {
        this.routingKey = routingKey;
        this.payload = payload;
    }

    public Long getId() { return id; }
    public String getRoutingKey() { return routingKey; }
    public String getPayload() { return payload; }
}
