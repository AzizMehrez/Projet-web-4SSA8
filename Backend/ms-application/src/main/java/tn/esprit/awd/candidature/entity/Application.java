package tn.esprit.awd.candidature.entity;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "applications", uniqueConstraints = @UniqueConstraint(
        name = "uk_application_candidate_job", columnNames = {"candidate_id", "job_id"}))
public class Application {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "candidate_id", nullable = false)
    private Long candidateId;
    @Column(name = "job_id", nullable = false)
    private Long jobId;
    @Column(nullable = false)
    private LocalDate applicationDate;
    @Column(length = 2000)
    private String motivation;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private Status status;
    @Version
    private long version;

    public enum Status { SUBMITTED, UNDER_REVIEW, SHORTLISTED, INTERVIEW, ACCEPTED, REJECTED, WITHDRAWN }

    protected Application() {
    }

    public Application(Long candidateId, Long jobId, LocalDate date, String motivation) {
        this.candidateId = candidateId;
        this.jobId = jobId;
        this.status = Status.SUBMITTED;
        update(date, motivation);
    }

    public void update(LocalDate date, String motivation) {
        this.applicationDate = date;
        this.motivation = motivation;
    }

    public void changeStatus(Status status) { this.status = status; }
    public Long getId() { return id; }
    public Long getCandidateId() { return candidateId; }
    public Long getJobId() { return jobId; }
    public LocalDate getApplicationDate() { return applicationDate; }
    public String getMotivation() { return motivation; }
    public Status getStatus() { return status; }
}
